"""門診成績單：逐句產生 HsiaoChen 旁白與音效，輸出 audio/mix.wav 與 timing.json。

python make_audio.py [YYYY_MM]（省略則用 data 裡最新的月份）
"""
import asyncio
import json
import math
import random
import struct
import subprocess
import sys
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg

from content import blocking_issues, lines, load

ROOT = Path(__file__).parent
AUDIO = ROOT / "audio"
AUDIO.mkdir(exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100
VOICE = "zh-TW-HsiaoChenNeural"
GAP = 0.3
SCENE_GAP = 0.55
LEAD_IN = 0.7
TAIL = 2.5

async def tts(text, path):
    await edge_tts.Communicate(text, VOICE).save(str(path))


def to_samples(path):
    raw = subprocess.run(
        [FF, "-hide_banner", "-loglevel", "error", "-i", str(path),
         "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, capture_output=True).stdout
    return list(struct.unpack(f"<{len(raw) // 2}h", raw))


def trim(s, thr=250):
    a, b = 0, len(s)
    while a < b and abs(s[a]) < thr:
        a += 1
    while b > a and abs(s[b - 1]) < thr:
        b -= 1
    return s[max(0, a - 600):min(len(s), b + 1500)]


def add(buf, start, samples, gain=1.0):
    i = int(start * SR)
    for j, v in enumerate(samples):
        k = i + j
        if 0 <= k < len(buf):
            buf[k] += v * gain


rng = random.Random(11)


def whoosh(d=0.32):
    n, out, lp = int(d * SR), [], 0.0
    for i in range(n):
        t = i / n
        a = 0.02 + 0.5 * t if t < 0.6 else 0.32 * (1 - t) / 0.4
        lp += (0.05 + 0.5 * t) * (rng.uniform(-1, 1) - lp)
        out.append(lp * a * 20000)
    return out


def thud(d=0.5, f0=110):
    out, ph = [], 0.0
    for i in range(int(d * SR)):
        t = i / SR
        ph += 2 * math.pi * f0 * (1 + 1.8 * math.exp(-t * 26)) / SR
        out.append(math.sin(ph) * math.exp(-t * 8) * 18000)
    return out


def ding(f=880, d=0.45):
    out = []
    for i in range(int(d * SR)):
        t = i / SR
        out.append((math.sin(2 * math.pi * f * t) + 0.4 * math.sin(4 * math.pi * f * t)) * math.exp(-t * 8) * 7500)
    return out


def rise(d=0.7):
    out = []
    for i in range(int(d * SR)):
        t = i / SR
        out.append(math.sin(2 * math.pi * 400 * 2 ** (t / d) * t) * math.sin(math.pi * t / d) * 5000)
    return out


async def main():
    D = load(sys.argv[1] if len(sys.argv) > 1 else None)
    bad = blocking_issues(D)
    if bad:
        raise SystemExit("還有問題沒處理，請先看 monthly.py check：\n" + "\n".join(f"- {k or '資料'}：{m}" for k, m in bad))
    voices, segs, t = [], [], LEAD_IN
    for i, ln in enumerate(lines(D)):
        if ln.get("new"):
            t += SCENE_GAP
        p = AUDIO / f"line{i:02d}.mp3"
        await tts(ln["say"], p)
        s = trim(to_samples(p))
        d = len(s) / SR
        segs.append(dict(k=ln["k"], new=bool(ln.get("new")), sub=ln.get("sub") or ln["say"].rstrip("，。？"),
                         start=round(t, 3), end=round(t + d, 3)))
        voices.append((t, s))
        t += d + GAP
    total = t + TAIL
    buf = [0.0] * int(total * SR)
    for st, s in voices:
        add(buf, st, s)
    S = {x["k"]: x["start"] for x in segs}

    for x in segs:
        if x["new"]:
            add(buf, x["start"] - 0.4, whoosh(), 0.5)
    add(buf, S["ppl1"] + 0.1, rise(0.6), 0.4)
    add(buf, S["ppl3"] + 1.2, thud(), 0.6)
    for k in range(5):
        add(buf, S["dis1"] + 0.1 + k * 0.28, ding(620 + k * 90, 0.3), 0.32)
    for k in range(3):
        add(buf, S["dis3"] + 1.1 + k * 0.28, ding(740 + k * 120, 0.3), 0.4)
    add(buf, S["tx1"] + 0.2, rise(0.9), 0.35)
    add(buf, S["eff1"] + 1.0, rise(0.8), 0.4)
    add(buf, S["eff1"] + 1.9, thud(0.5, 130), 0.55)
    add(buf, S["eff3"] + 0.2, rise(1.0), 0.3)
    for k in range(4):
        add(buf, S["tr1"] + 0.15 + k * 0.42, ding(560 + k * 110, 0.35), 0.38)
    for k in range(4):
        add(buf, S["bud1"] + 0.1 + k * 0.28, ding(620 + k * 90, 0.3), 0.3)
    add(buf, S["end1"] + 0.1, thud(0.5, 150), 0.45)
    add(buf, S["end1"] + 0.2, ding(990, 0.6), 0.45)

    peak = max(abs(v) for v in buf) or 1
    scale = min(1.0, 30000 / peak)
    with wave.open(str(AUDIO / "mix.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(v * scale)) for v in buf))
    (ROOT / "timing.json").write_text(
        json.dumps(dict(month=D["month"], total=round(total, 3), segments=segs), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"total {total:.2f}s")
    for x in segs:
        print(x["start"], x["end"], x["k"])


asyncio.run(main())
