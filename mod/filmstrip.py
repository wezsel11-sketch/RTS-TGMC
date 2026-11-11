#!/usr/bin/env python3
"""Join screenshots into one filmstrip: filmstrip.py out.png frame1.png frame2.png ...

Keeps the middle STRIP_CROP (default 640x400) of each frame, at full size so a 32 px effect stays readable, four to a row, in the
order given (mod/shots.sh passes them sorted by name, which is the order they were taken in).
"""
import os
import sys

from PIL import Image


def main():
    out, frames = sys.argv[1], sys.argv[2:]
    w, h = (int(x) for x in os.environ.get("STRIP_CROP", "640x400").split("x"))
    cols = min(4, len(frames))
    strip = Image.new("RGB", (cols * w, -(-len(frames) // cols) * h))
    for i, path in enumerate(frames):
        img = Image.open(path).convert("RGB")
        left, top = (img.width - w) // 2, (img.height - h) // 2
        strip.paste(img.crop((left, top, left + w, top + h)), (i % cols * w, i // cols * h))
    strip.save(out)


if __name__ == "__main__":
    main()
