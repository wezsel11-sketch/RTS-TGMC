"""Cut the terrain tiles the TGMC tileset uses out of TGMC's .dmi sheets, as single-frame PNGs for OpenRA.

  TILES maps an output name to (dmi path, state name, frame). Every TGMC floor tile is 32x32.

Output (default build/mod/tgmc): <name>.png per tile, each tagged with FrameSize and FrameAmount, and
tiles.json with each tile's average colour (use it to keep `Color` in tilesets/ground.yaml honest).

Usage: build_tileset.py --tgmc CHECKOUT [--out DIR]
"""
import argparse
import json
import math
import os
import sys

from PIL import Image, PngImagePlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgmc_dmi  # noqa: E402

JUNGLE = "icons/turf/jungle.dmi"
GROUND = "icons/turf/ground_map.dmi"
CAVE = "icons/turf/walls/cave.dmi"

# TGMC's jungle grass is bright blades on near-black: tiled over a whole map it shimmers and hides the units standing on it.
# SOFTEN pulls each pixel of a tile this far (0 to 1) toward the average colour of all the softened tiles together, so patches
# of grass1 and grass2 do not read as a checkerboard either.
SOFTEN = {"grass1": 0.7, "grass2": 0.7}

TILES = {
    "grass1": (JUNGLE, "grass1", 0),
    "grass2": (JUNGLE, "grass2", 0),
    "dirt": (GROUND, "dirt", 0),
    "ford": (GROUND, "seashallow", 0),
    "water": (GROUND, "seadeep", 0),
    "rock": (CAVE, "cave-255", 0),
    "wall": (CAVE, "cave-255", 0),
}

# Tiles that meet grass get an edge sheet, <name>-edge.png: 16 frames, frame m with grass grown in from the sides named by the
# bits of m (1 north, 2 east, 4 south, 8 west). Frame 0 is the plain tile. mod/make_placeholders.py picks the frame from a
# cell's four neighbours, so a shore or a road side is a ragged line of grass and not a ruler-straight tile border.
EDGES = ("water", "ford", "dirt")
EDGE_DEPTH = 7  # pixels of grass at the deepest

# Rock and wall tiles are TGMC's own cave pieces, one for each way a rock cell can join its neighbours: rock-edge.png and
# wall-edge.png hold them in this order. A number is TGMC's smoothing junction: 1 north, 2 south, 4 east, 8 west, 16 north-east,
# 32 south-east, 64 south-west, 128 north-west, added up; a corner counts only when both sides beside it are rock.
CAVE_JUNCTIONS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 21, 23, 29, 31, 38, 39, 46, 47, 55, 63, 74, 75, 78, 79, 95,
                  110, 111, 127, 137, 139, 141, 143, 157, 159, 175, 191, 203, 207, 223, 239, 255)


def cave_frame(rock):
    """The frame of the rock sheets for a cell: rock(dx, dy) says whether the neighbour that way is rock too."""
    n, s, e, w = rock(0, -1), rock(0, 1), rock(1, 0), rock(-1, 0)
    junction = n * 1 + s * 2 + e * 4 + w * 8
    junction += 16 * (n and e and rock(1, -1)) + 32 * (s and e and rock(1, 1))
    junction += 64 * (s and w and rock(-1, 1)) + 128 * (n and w and rock(-1, -1))
    return CAVE_JUNCTIONS.index(junction)


def edge_sheet(base, grass):
    """The 16 edge frames of `base` side by side."""
    def reach(t):
        # How far the grass comes in at position t along a side: two waves that both repeat every 32 px, so tiles line up.
        return EDGE_DEPTH * (0.62 + 0.25 * math.sin(2 * math.pi * t / 32 * 2 + 1.0) + 0.13 * math.sin(2 * math.pi * t / 32 * 5))

    sheet = Image.new("RGB", (32 * 16, 32))
    for m in range(16):
        mask = Image.new("L", (32, 32), 0)
        px = mask.load()
        for y in range(32):
            for x in range(32):
                a = 0.0
                # (distance in from the side, position along it) for each side that has grass beyond it
                for bit, d, t in ((1, y, x), (2, 31 - x, y), (4, 31 - y, x), (8, x, y)):
                    if m & bit:
                        a = max(a, min(1.0, max(0.0, (reach(t) - d) / 2)))
                px[x, y] = round(255 * a)
        frame = base.convert("RGB").copy()
        frame.paste(grass.convert("RGB"), (0, 0), mask)
        sheet.paste(frame, (32 * m, 0))
    return sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", required=True, help="path to a terragov-marine-corps checkout")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "mod", "tgmc"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    dmis = {}
    report = {}
    for path in {spec[0] for spec in TILES.values()}:
        dmis[path] = tgmc_dmi.Dmi(os.path.join(args.tgmc, path))
    means = [dmis[TILES[n][0]].frames(TILES[n][1])[TILES[n][2]][0].convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0)) for n in SOFTEN]
    soft = tuple(sum(m[i] for m in means) // len(means) for i in range(3))
    made = {}
    for name, (path, state, frame) in sorted(TILES.items()):
        dmi = dmis[path]
        img = dmi.frames(state)[frame][0]
        if img.size != (32, 32):
            raise SystemExit(f"{path}:{state} is {img.size}, expected 32x32")
        if name in SOFTEN:
            img = Image.blend(img.convert("RGB"), Image.new("RGB", img.size, soft), SOFTEN[name])
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", "32,32")
        meta.add_text("FrameAmount", "1")
        img.save(os.path.join(args.out, f"{name}.png"), pnginfo=meta)
        made[name] = img
        r, g, b = img.convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0))
        report[name] = f"{r:02X}{g:02X}{b:02X}"
        print(f"{name}.png <- {path}:{state}  average colour {report[name]}")
    for name in EDGES:
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", "32,32")
        meta.add_text("FrameAmount", "16")
        edge_sheet(made[name], made["grass1"]).save(os.path.join(args.out, f"{name}-edge.png"), pnginfo=meta)
    cave = dmis[CAVE]
    sheet = Image.new("RGB", (32 * len(CAVE_JUNCTIONS), 32))
    for i, junction in enumerate(CAVE_JUNCTIONS):
        sheet.paste(cave.frames(f"cave-{junction}")[0][0].convert("RGB"), (32 * i, 0))
    for name in ("rock", "wall"):
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", "32,32")
        meta.add_text("FrameAmount", str(len(CAVE_JUNCTIONS)))
        sheet.save(os.path.join(args.out, f"{name}-edge.png"), pnginfo=meta)
    with open(os.path.join(args.out, "tiles.json"), "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
