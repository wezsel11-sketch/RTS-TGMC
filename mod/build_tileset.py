"""Cut the terrain tiles the TGMC tileset uses out of TGMC's .dmi sheets, as single-frame PNGs for OpenRA.

  TILES maps an output name to (dmi path, state name, frame[, options]). Every TGMC floor tile is 32x32. The options are
  "mul": (r, g, b) multiplies the colours by r/255, g/255, b/255 (darken or tint a tile that is the wrong shade),
  "edge": (r, g, b) draws a one-pixel border of that colour, which makes a wall tile read as a raised block.

Output (default build/mod/tgmc): <name>.png per tile, each tagged with FrameSize and FrameAmount, and
tiles.json with each tile's average colour (use it to keep `Color` in tilesets/ground.yaml honest).

Usage: build_tileset.py --tgmc CHECKOUT [--out DIR]
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageChops, ImageDraw, PngImagePlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgmc_dmi  # noqa: E402

JUNGLE = "icons/turf/jungle.dmi"
GROUND = "icons/turf/ground_map.dmi"
CAVE_WALL = "icons/turf/walls/cave.dmi"
JUNGLE_WALL = "icons/turf/walls/junglewall.dmi"
FLOORS = "icons/turf/floors.dmi"

TILES = {
    "grass1": (JUNGLE, "grass1", 0),
    "grass2": (JUNGLE, "grass2", 0),
    "dirt": (GROUND, "dirt", 0),
    "ford": (GROUND, "seashallow", 0),
    "water": (GROUND, "seadeep", 0),
    # Terrain for the LV-624 map (mod/build_map.py): rock and cave floor, dense jungle, colony walls and floors
    "rock1": (CAVE_WALL, "cave-63", 0, {"mul": (150, 130, 112)}),
    "rock2": (CAVE_WALL, "cave-127", 0, {"mul": (136, 118, 102)}),
    "brush": (JUNGLE_WALL, "junglewall-255", 0, {"mul": (170, 190, 160)}),
    "wall": (FLOORS, "plating", 0, {"mul": (235, 240, 245), "edge": (200, 208, 214)}),
    "floor": (FLOORS, "floor", 0),
    "plating": (FLOORS, "dark", 0),
    "cavedirt": (GROUND, "dirt", 0, {"mul": (176, 160, 150)}),
}


def adjust(img, opts):
    """Apply a TILES entry's "mul" and "edge" options to a 32x32 tile."""
    if "mul" in opts:
        r, g, b, a = img.convert("RGBA").split()
        rgb = Image.merge("RGB", (r, g, b))
        img = ImageChops.multiply(rgb, Image.new("RGB", rgb.size, opts["mul"])).convert("RGBA")
        img.putalpha(a)
    if "edge" in opts:
        img = img.convert("RGBA")
        ImageDraw.Draw(img).rectangle([0, 0, img.width - 1, img.height - 1], outline=tuple(opts["edge"]) + (255,))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", required=True, help="path to a terragov-marine-corps checkout")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "mod", "tgmc"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    dmis = {}
    report = {}
    for name, (path, state, frame, *rest) in sorted(TILES.items()):
        if path not in dmis:
            dmis[path] = tgmc_dmi.Dmi(os.path.join(args.tgmc, path))
        dmi = dmis[path]
        img = dmi.frames(state)[frame][0]
        if rest:
            img = adjust(img, rest[0])
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
