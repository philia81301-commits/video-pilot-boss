"""健康旅程攻略：逐句配音、原配樂、音效，輸出 audio/mix.wav 與 timing.json。

配樂用舊片同一支程式（music_upbeat.py）依片長重新合成，所以曲子不變。
語音檔依文字快取，改句子時只重做改到的句子。
"""
import asyncio
import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np

from script import SCENES

ROOT = Path(__file__).parent
AUDIO = ROOT / "audio"
AUDIO.mkdir(exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100
VOICE = "zh-TW-HsiaoChenNeural"
MUSIC = Path(r"C:\projects\obesity-education-clinic\video\journey-guide\music_upbeat.py")
GAP = 0.32
SCENE_GAP = 0.7
LEAD_IN = 1.4
MUSIC_UNDER_VOICE = 0.20
MUSIC_OPEN = 0.46
rng = np.random.default_rng(7)


async def tts(text):
    path = AUDIO / f"v_{hashlib.md5((VOICE + text).encode()).hexdigest()[:12]}.mp3"
    if not path.exists():
        await edge_tts.Communicate(text, VOICE).save(str(path))
    return path


def to_samples(path):
    raw = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1",
                          "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768


def trim(s, thr=0.008):
    idx = np.nonzero(np.abs(s) > thr)[0]
    return s[max(0, idx[0] - 600):min(len(s), idx[-1] + 1500)]


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def whoosh(d=0.32):
    t = tt(d)
    n = rng.standard_normal(len(t))
    n = np.convolve(n, np.ones(9) / 9, "same")
    return n * np.sin(np.pi * t / d) ** 2 * 0.55


def thud(d=0.5, f0=110):
    t = tt(d)
    return np.sin(2 * np.pi * np.cumsum(f0 * (1 + 1.8 * np.exp(-t * 26))) / SR) * np.exp(-t * 8) * 0.55


def ding(f=880, d=0.45):
    t = tt(d)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 8) * 0.22


def rise(d=0.7):
    t = tt(d)
    return np.sin(2 * np.pi * 400 * 2 ** (t / d) * t) * np.sin(np.pi * t / d) * 0.15


def alert(d=0.28):
    t = tt(d)
    return (np.sin(2 * np.pi * 660 * t) + np.sin(2 * np.pi * 880 * t)) * np.exp(-t * 7) * 0.13


async def main():
    voices, t, seg_out, scene_out = [], LEAD_IN, [], []
    for si, sc in enumerate(SCENES):
        if si:
            t += SCENE_GAP
        start = t
        for li, ln in enumerate(sc["lines"]):
            s = trim(to_samples(await tts(ln["say"])))
            d = len(s) / SR
            sub = ln.get("sub") or ln.get("text") or ln["say"]
            seg_out.append(dict(s=si, i=li, sub=sub.rstrip("，。"), start=round(t, 3), end=round(t + d, 3)))
            voices.append((t, s))
            t += d + GAP
        t += sc.get("hold", 0.5)
        scene_out.append(dict(start=round(start, 3), end=round(t, 3)))
    total = t + 1.5
    print(f"片長 {int(total // 60)} 分 {total % 60:.1f} 秒")

    bgm = AUDIO / f"bgm_{int(total + 1)}.wav"
    if not bgm.exists():
        subprocess.run([sys.executable, str(MUSIC), str(int(total + 1)), str(bgm)], check=True)
    with wave.open(str(bgm)) as w:
        music = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64).reshape(-1, 2) / 32768

    n = int(total * SR)
    music = music[:n]
    if len(music) < n:
        music = np.vstack([music, np.zeros((n - len(music), 2))])

    voice = np.zeros(n)
    duck = np.zeros(n)
    for st, s in voices:
        i = int(st * SR)
        voice[i:i + len(s)] += s[:n - i]
        duck[max(0, i - int(0.25 * SR)):i + len(s) + int(0.25 * SR)] = 1
    k = int(0.3 * SR)
    cum = np.concatenate([[0.0], np.cumsum(duck)])
    half = k // 2
    duck = (cum[np.minimum(np.arange(n) + half, n)] - cum[np.maximum(np.arange(n) - half, 0)]) / k
    gain = MUSIC_OPEN + (MUSIC_UNDER_VOICE - MUSIC_OPEN) * duck

    fx = np.zeros(n)

    def add(start, sig, g=1.0):
        i = int(start * SR)
        if 0 <= i < n:
            m = min(len(sig), n - i)
            fx[i:i + m] += sig[:m] * g

    for si, sc in enumerate(SCENES):
        st = scene_out[si]["start"]
        segs = [x for x in seg_out if x["s"] == si]
        if si:
            add(st - 0.42, whoosh(), 0.5)
        if sc["type"] in ("chapter", "intro", "outro"):
            add(st + 0.05, rise(0.8), 0.7)
            add(st + 0.5, thud(0.5, 150), 0.5)
        for x, ln in zip(segs, sc["lines"]):
            kind = ln["kind"]
            if kind in ("li", "p"):
                add(x["start"], ding(740 + x["i"] * 70, 0.3), 0.45)
            elif kind == "hl":
                add(x["start"], rise(0.5), 0.5)
                add(x["start"] + 0.3, ding(990, 0.5), 0.55)
            elif kind == "task":
                add(x["end"] - 0.15, ding(880 + x["i"] * 90, 0.4), 0.7)
            elif kind == "flag":
                add(x["start"], alert(), 0.8)
            elif kind == "call":
                add(x["start"], thud(0.4, 130), 0.5)
    mono = voice + fx
    mix = music * gain[:, None] + mono[:, None]
    mix = mix / max(np.max(np.abs(mix)), 1e-6) * 0.92
    with wave.open(str(AUDIO / "mix.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    (ROOT / "timing.json").write_text(
        json.dumps(dict(total=round(total, 3), scenes=scene_out, segments=seg_out), ensure_ascii=False, indent=1), encoding="utf-8")


asyncio.run(main())
