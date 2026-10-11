"""Cut the terrain tiles the TGMC tileset uses out of TGMC's .dmi sheets, as single-frame PNGs for OpenRA.

  TILES maps an output name to (dmi path, state name, frame). Every TGMC floor tile is 32x32.

Output (default build/mod/tgmc): <name>.png per tile, each tagged with FrameSize and FrameAmount, and
tiles.json with each tile's average colour (use it to keep `Color` in tilesets/ground.yaml honest).

Usage: build_tileset.py --tgmc CHECKOUT [--out DIR]
"""
import argparse
import json
import os
import sys

from PIL import Image, PngImagePlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgmc_dmi  # noqa: E402

JUNGLE = "icons/turf/jungle.dmi"
GROUND = "icons/turf/ground_map.dmi"

TILES = {
    "grass1": (JUNGLE, "grass1", 0),
    "grass2": (JUNGLE, "grass2", 0),
    "dirt": (GROUND, "dirt", 0),
    "ford": (GROUND, "seashallow", 0),
    "water": (GROUND, "seadeep", 0),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", required=True, help="path to a terragov-marine-corps checkout")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "mod", "tgmc"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    dmis = {}
    report = {}
    for name, (path, state, frame) in sorted(TILES.items()):
        if path not in dmis:
            dmis[path] = tgmc_dmi.Dmi(os.path.join(args.tgmc, path))
        dmi = dmis[path]
        img = dmi.frames(state)[frame][0]
        if img.size != (32, 32):
            raise SystemExit(f"{path}:{state} is {img.size}, expected 32x32")
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", "32,32")
        meta.add_text("FrameAmount", "1")
        img.save(os.path.join(args.out, f"{name}.png"), pnginfo=meta)
        r, g, b = img.convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0))
        report[name] = f"{r:02X}{g:02X}{b:02X}"
        print(f"{name}.png <- {path}:{state}  average colour {report[name]}")
    with open(os.path.join(args.out, "tiles.json"), "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
