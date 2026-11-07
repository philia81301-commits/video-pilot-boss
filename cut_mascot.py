"""把吉祥物貼圖的底色去掉：從四角往內填色，保留貼紙白邊。"""
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent / "assets"


def cut(name, tol=38):
    im = Image.open(ROOT / f"{name}.png").convert("RGBA")
    w, h = im.size
    px = im.load()
    bg = px[2, 2][:3]
    seen = set()
    q = deque([(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)])
    while q:
        x, y = q.popleft()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        seen.add((x, y))
        r, g, b, _ = px[x, y]
        if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > tol:
            continue
        px[x, y] = (r, g, b, 0)
        q.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    im.save(ROOT / f"{name}-cut.png")
    print(name, im.size, "transparent", len(seen))


cut("s3-mascot")
cut("s3-badge")
