"""把每一幕結尾的畫面拼成總表，方便一次檢查版面。python sheet.py [幕的編號...]"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
OUT = ROOT / "out"
timing = json.loads((ROOT / "timing.json").read_text(encoding="utf-8"))
scenes = timing["scenes"]
ids = [int(x) for x in sys.argv[1:]] or list(range(len(scenes)))
times = [round(scenes[i]["end"] - 0.15, 2) for i in ids]
subprocess.run([sys.executable, "render.py", "snap", *map(str, times)], check=True, cwd=ROOT)
CELL, COLS, ROWS = (800, 450), 2, 3
for page in range(0, len(ids), COLS * ROWS):
    sheet = Image.new("RGB", (CELL[0] * COLS, CELL[1] * ROWS), "black")
    for k, t in enumerate(times[page:page + COLS * ROWS]):
        f = OUT / f"snap_{t:06.2f}.jpg"
        sheet.paste(Image.open(f).resize(CELL), ((k % COLS) * CELL[0], (k // COLS) * CELL[1]))
        f.unlink()
    dest = OUT / f"sheet_{page // (COLS * ROWS)}.jpg"
    sheet.save(dest, quality=82)
    print(dest)
