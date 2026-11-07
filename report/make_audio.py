"""門診成績單：逐句產生 HsiaoChen 旁白與音效，輸出 audio/mix.wav 與 timing.json。"""
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
GAP = 0.3
SCENE_GAP = 0.55
LEAD_IN = 0.7
TAIL = 2.5

# k：動畫錨點；say：唸的文字；sub：字幕（省略則用 say）；new：是否新場景
LINES = [
    dict(k="intro1", say="大家好，這裡是高雄榮總家醫部減重門診。"),
    dict(k="intro2", say="帶你看看，門診夥伴的真實數據。"),
    dict(k="ppl1", new=1, say="目前累積追蹤八百八十三位個案，", sub="目前累積追蹤 883 位個案"),
    dict(k="ppl2", say="平均四十二點七歲，起始體重平均九十點九公斤。", sub="平均 42.7 歲，起始體重平均 90.9 公斤"),
    dict(k="ppl3", say="來診前半年，百分之七十一的人，體重正在上升。", sub="來診前半年，71% 的人體重正在上升"),
    dict(k="ppl4", say="你不孤單，來看診的人，大多和你一樣正在努力。"),
    dict(k="dis1", new=1, say="常合併的健康問題，第一名是糖尿病或糖尿病前期，超過三成五。",
         sub="常合併的健康問題，第一名是糖尿病或前期，超過三成五"),
    dict(k="dis2", say="脂肪肝、高血脂、高血壓，也都在三成上下。"),
    dict(k="dis3", say="大約每四個人，就有三個人合併至少一種健康問題。"),
    dict(k="dis4", say="好消息是，體重下降，這些問題也常跟著改善。"),
    dict(k="tx1", new=1, say="治療方式呢？腸泌素藥物佔百分之四十三，生活型態調整不用藥，佔百分之三十四。",
         sub="腸泌素藥物 43%，生活型態調整（不用藥）34%"),
    dict(k="tx2", say="用不用藥、用哪一種，都由醫師依你的身體狀況一起討論。"),
    dict(k="eff1", new=1, say="追蹤三到五個月，平均體重下降百分之五點六。", sub="追蹤 3 到 5 個月，平均體重下降 5.6%"),
    dict(k="eff2", say="以八十公斤為例，大約減四點五公斤。", sub="以 80 公斤為例，大約減 4.5 公斤"),
    dict(k="eff3", say="有一半的人，減掉百分之五以上的體重，這是醫學上有意義的改善。",
         sub="一半的人（51%）減掉 5% 以上體重，這是醫學上有意義的改善"),
    dict(k="tr1", new=1, say="追蹤半年以上的人，平均減重大約百分之八到十。", sub="追蹤半年以上的人，平均減重大約 8% 到 10%"),
    dict(k="tr2", say="穩穩減、持續回診，比一次減很多更重要。"),
    dict(k="bud1", new=1, say="初診問卷裡，將近一半的人，可以接受每月八千到一萬五千元。",
         sub="將近一半的人，可接受每月 8,000 到 15,000 元"),
    dict(k="bud2", say="看診時可以依你的預算，和醫師一起規劃方案。"),
    dict(k="end1", new=1, say="減重，我們陪你一起走。"),
    dict(k="end2", say="個人成效因人而異，實際治療以醫師評估為準。"),
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
    voices, segs, t = [], [], LEAD_IN
    for i, ln in enumerate(LINES):
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
        json.dumps(dict(total=round(total, 3), segments=segs), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"total {total:.2f}s")
    for x in segs:
        print(x["start"], x["end"], x["k"])


asyncio.run(main())
