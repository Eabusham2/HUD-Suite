"""Run after `python build.py`: is the committed packs/ folder what build.py makes?

Text files must match byte-for-byte. PNGs must match pixel-for-pixel (their compressed bytes
depend on the zlib build Pillow uses, so bytes alone can differ on another machine).
Exit code 1 = packs/ is out of date: run `python build.py` and commit packs/.
"""
import io, os, subprocess, sys
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, check=True)

def pixels(data):
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    return im.size, im.tobytes()

out_of_date = []
for line in git("status", "--porcelain", "--", "packs").stdout.decode().splitlines():
    status, path = line[:2].strip(), line[3:]
    if status == "M" and path.endswith(".png"):
        if pixels(git("show", f"HEAD:{path}").stdout) == pixels(open(os.path.join(ROOT, path), "rb").read()):
            continue
    out_of_date.append(line)

if out_of_date:
    print("packs/ differs from what build.py makes:")
    print("\n".join(out_of_date))
    sys.exit(1)
print("packs/ is up to date (text byte-for-byte, images pixel-for-pixel).")
