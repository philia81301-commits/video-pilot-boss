"""逐格輸出。

python render.py snap 1.5 4.2 ...：指定秒數的畫面
python render.py full：完整影片、手機版與封面
月份一律跟 timing.json（由 make_audio.py 決定），避免畫面和配音對不上。
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

from content import load, page_data

ROOT = Path(__file__).parent
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
FPS = 30
timing = json.loads((ROOT / "timing.json").read_text(encoding="utf-8"))
FF = imageio_ffmpeg.get_ffmpeg_exe()
MONTH = timing["month"]
D = load(MONTH)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script(f"window.TIMING = {json.dumps(timing, ensure_ascii=False)};")
    page.add_init_script(f"window.DATA = {json.dumps(page_data(D), ensure_ascii=False)};")
    page.goto((ROOT / "index.html").as_uri())
    page.evaluate("document.fonts.ready")
    page.evaluate("Promise.all([...document.images].map(i => i.decode().catch(() => {})))")

    if sys.argv[1] == "snap":
        for t in sys.argv[2:]:
            page.evaluate("t => render(t)", float(t))
            page.screenshot(path=str(OUT / f"snap_{float(t):06.2f}.jpg"), type="jpeg", quality=80)
        print("snap ok", "errors:", errors)
    else:
        frames = int(timing["total"] * FPS)
        dest = OUT / f"report-{MONTH}.mp4"
        ff = subprocess.Popen(
            [FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
             "-i", str(ROOT / "audio" / "mix.wav"), "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p",
             "-color_range", "tv", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
             "-shortest", "-movflags", "+faststart", str(dest)],
            stdin=subprocess.PIPE)
        t0 = time.time()
        for f in range(frames):
            page.evaluate("t => render(t)", f / FPS)
            ff.stdin.write(page.screenshot(type="jpeg", quality=93))
            if f % 300 == 0:
                print(f"{f}/{frames} {time.time() - t0:.0f}s", flush=True)
        ff.stdin.close()
        ff.wait()
        print("done", dest, f"{dest.stat().st_size / 1e6:.1f} MB", "errors:", errors)
        # 手機與網站用 720p；封面取片頭有標題和月份的畫面
        phone = OUT / f"report-{MONTH}-phone.mp4"
        subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", str(dest), "-vf", "scale=1280:-2",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart", str(phone)], check=True)
        poster = OUT / f"report-{MONTH}-poster.jpg"
        subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", "3", "-i", str(dest), "-frames:v", "1",
                        "-vf", "scale=1280:-2", "-q:v", "3", str(poster)], check=True)
        print("phone", phone, f"{phone.stat().st_size / 1e6:.1f} MB", "poster", poster)
    browser.close()
