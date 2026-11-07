"""逐句產生 HsiaoChen 旁白與音效，輸出 audio/mix.wav 和 timing.json。"""
import asyncio
import json
import math
import random
import struct
import subprocess
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg

ROOT = Path(__file__).parent
AUDIO = ROOT / "audio"
AUDIO.mkdir(exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100
VOICE = "zh-TW-HsiaoChenNeural"
GAP = 0.28
LEAD_IN = 0.6
TAIL = 1.6

LINES = [
    "體重卡住了，先別慌。",
    "這就是停滯期，也就是減重路上的魔王關。",
    "這是身體的生理反應，不是你失敗。",
    "先不要急著吃更少。",
    "打贏魔王靠三招：",
    "肌力訓練加量，",
    "把步數補回來，",
    "吃得抗餓。",
    "腸泌素針劑不要自己停，",
    "卡超過兩個月，回診我們一起找原因。",
]


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
        if k >= len(buf):
            break
        buf[k] += v * gain


rng = random.Random(7)


def sfx_whoosh(d=0.35):
    n, out, lp = int(d * SR), [], 0.0
    for i in range(n):
        t = i / n
        a = 0.02 + 0.5 * t if t < 0.6 else 0.32 * (1 - t) / 0.4
        lp += (0.05 + 0.5 * t) * (rng.uniform(-1, 1) - lp)
        out.append(lp * a * 22000)
    return out


def sfx_impact(d=0.7, f0=90):
    n, out = int(d * SR), []
    ph = 0.0
    for i in range(n):
        t = i / SR
        f = f0 * (1 + 2.2 * math.exp(-t * 28))
        ph += 2 * math.pi * f / SR
        out.append((math.sin(ph) * math.exp(-t * 6) + rng.uniform(-1, 1) * 0.3 * math.exp(-t * 30)) * 21000)
    return out


def sfx_ding(f=880, d=0.5):
    n, out = int(d * SR), []
    for i in range(n):
        t = i / SR
        v = math.sin(2 * math.pi * f * t) + 0.45 * math.sin(2 * math.pi * f * 2 * t)
        out.append(v * math.exp(-t * 7) * 8500)
    return out


def sfx_rise(d=0.6):
    out = []
    for i in range(int(d * SR)):
        t = i / SR
        f = 440 * 2 ** (t / d * 1.0)
        out.append(math.sin(2 * math.pi * f * t) * math.sin(math.pi * t / d) * 6500)
    return out


async def main():
    voices, segs, t = [], [], LEAD_IN
    for i, line in enumerate(LINES):
        p = AUDIO / f"line{i:02d}.mp3"
        await tts(line, p)
        s = trim(to_samples(p))
        d = len(s) / SR
        segs.append({"i": i, "text": line, "start": round(t, 3), "end": round(t + d, 3)})
        voices.append((t, s))
        t += d + (GAP if i not in (4,) else 0.15)
    total = t + TAIL
    buf = [0.0] * int(total * SR)
    for st, s in voices:
        add(buf, st, s)

    S = {x["i"]: x["start"] for x in segs}
    add(buf, S[1] + 1.0, sfx_impact(0.9, 70), 0.75)       # 魔王落地
    add(buf, S[1] + 0.85, sfx_whoosh(0.2), 0.5)
    add(buf, S[2] + 0.05, sfx_ding(660), 0.45)
    add(buf, S[3] + 0.5, sfx_whoosh(0.25), 0.4)
    for k, idx in enumerate((5, 6, 7)):                    # 三招命中
        add(buf, S[idx] - 0.05, sfx_whoosh(0.25), 0.45)
        add(buf, S[idx] + 0.3, sfx_impact(0.4, 130 + k * 25), 0.5)
    add(buf, S[9] + 0.2, sfx_rise(0.6), 0.4)

    peak = max(abs(v) for v in buf) or 1
    scale = min(1.0, 30000 / peak)
    with wave.open(str(AUDIO / "mix.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(v * scale)) for v in buf))
    (ROOT / "timing.json").write_text(
        json.dumps({"total": round(total, 3), "segments": segs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"total {total:.2f}s")
    for x in segs:
        print(x["start"], x["end"], x["text"])


asyncio.run(main())
