"""Generate the non-TGMC pieces the mod needs to load and show a test field.

Nothing here is TGMC art. It writes:
  tgmc.pal                      a flat grey 256-colour palette (OpenRA needs one for its palette setup)
  ground.png                    one 24x24 green ground tile for the terrain template
  cursor.png                    a plain arrow for the default cursor
  clock.png                     production-icon clock overlay frames (62x46, a dark wedge that sweeps away)
  maps/test-field/map.{yaml,bin,png}   a 24x24 map with marines, runners, and one of each structure
  maps/landing-zone/map.{yaml,bin,png} a 40x28 two-base skirmish map: marines west, xenos east

Usage: make_placeholders.py --out DIR
"""
import argparse
import math
import os
import struct

from PIL import Image, ImageDraw, PngImagePlugin

CLOCK_W, CLOCK_H, CLOCK_FRAMES, CLOCK_COLS = 62, 46, 30, 6  # matches the sidebar palette's IconSize
TILE_ID = 1  # Template@1 in tilesets/ground.yaml, which is the Clear ground tile

# (actor, owner, x, y, facing). Facing is in OpenRA angle units: 0 = north, 512 = south.
TEST_FIELD = [
    ("rifleman", "Marines", 9, 11, 0),
    ("rifleman", "Marines", 10, 11, 256),
    ("rifleman", "Marines", 11, 11, 512),
    ("runner", "Xenos", 13, 12, 0),
    ("runner", "Xenos", 14, 12, 256),
    ("runner", "Xenos", 15, 12, 512),
    ("resin-turret", "Xenos", 17, 10, 0),
    ("resin-silo", "Xenos", 4, 4, 0),
    ("mini-silo", "Xenos", 18, 4, 0),
    ("medic", "Marines", 9, 13, 512),
    ("engineer", "Marines", 10, 13, 512),
    ("sentry-turret", "Marines", 12, 8, 512),
    ("cryo-pod", "Marines", 5, 17, 512),
    ("vendor", "Marines", 19, 17, 512),
]

# Two bases facing each other across the middle. Exits are below the producers, so keep those cells clear.
LANDING_ZONE = [
    ("cryo-pod", "Marines", 4, 12, 512),
    ("vendor", "Marines", 7, 12, 512),
    ("sentry-turret", "Marines", 10, 11, 256),
    ("sentry-turret", "Marines", 10, 16, 256),
    ("rifleman", "Marines", 6, 16, 256),
    ("rifleman", "Marines", 7, 16, 256),
    ("rifleman", "Marines", 8, 16, 256),
    ("medic", "Marines", 6, 17, 256),
    ("engineer", "Marines", 7, 17, 256),
    ("resin-silo", "Xenos", 33, 12, 768),
    ("mini-silo", "Xenos", 36, 7, 768),
    ("mini-silo", "Xenos", 36, 18, 768),
    ("resin-turret", "Xenos", 30, 11, 768),
    ("resin-turret", "Xenos", 30, 16, 768),
    ("runner", "Xenos", 29, 13, 768),
    ("runner", "Xenos", 29, 14, 768),
    ("runner", "Xenos", 29, 15, 768),
    ("runner", "Xenos", 29, 12, 768),
]


def palette_entries():
    """A plain grey ramp. Only the palette-based paths read it; the TGMC-free tiles and sprites are RGBA."""
    return [(i, i, i) for i in range(256)]


def write_palette(path):
    with open(path, "wb") as f:
        f.write(bytes(c for rgb in palette_entries() for c in rgb))


def write_ground_tile(path):
    """RGBA, not indexed: OpenRA's indexed terrain path drew this tile in the wrong colours."""
    img = Image.new("RGBA", (24, 24), (0x3B, 0x5A, 0x2F, 255))
    px = img.load()
    for y in range(24):
        for x in range(24):
            if (x * 7 + y * 13) % 11 == 0:
                px[x, y] = (0x34, 0x51, 0x2A, 255)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", "24,24")
    meta.add_text("FrameAmount", "1")
    img.save(path, pnginfo=meta)


def write_cursor(path):
    """A plain arrow, drawn here so the mod has a cursor without any TGMC art."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y in range(12):
        for x in range(min(y + 1, 8)):
            px[x, y] = (255, 255, 255, 255) if x == 0 or x == y or y == 11 else (0, 0, 0, 255)
    img.save(path)


def write_clock(path):
    """Frame i darkens the part of the icon the production clock has not swept yet, clockwise from 12 o'clock."""
    rows = (CLOCK_FRAMES + CLOCK_COLS - 1) // CLOCK_COLS
    sheet = Image.new("RGBA", (CLOCK_COLS * CLOCK_W, rows * CLOCK_H), (0, 0, 0, 0))
    cx, cy, r = CLOCK_W / 2, CLOCK_H / 2, math.hypot(CLOCK_W, CLOCK_H)
    for i in range(CLOCK_FRAMES):
        frame = Image.new("RGBA", (CLOCK_W, CLOCK_H), (0, 0, 0, 0))
        if i < CLOCK_FRAMES - 1:
            start = -90 + 360 * i / (CLOCK_FRAMES - 1)
            ImageDraw.Draw(frame).pieslice([cx - r, cy - r, cx + r, cy + r], start, 270, fill=(0, 0, 0, 150))
        sheet.paste(frame, ((i % CLOCK_COLS) * CLOCK_W, (i // CLOCK_COLS) * CLOCK_H))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{CLOCK_W},{CLOCK_H}")
    meta.add_text("FrameAmount", str(CLOCK_FRAMES))
    sheet.save(path, pnginfo=meta)


def write_map(folder, title, size_w, size_h, placed, visibility):
    os.makedirs(folder, exist_ok=True)
    cells = size_w * size_h
    # map.bin: version byte, width, height, u32 tiles offset, u32 heights offset (0), u32 resources offset (0),
    # then per cell (x-major): u16 template id, u8 variant index.
    header = struct.pack("<BHHIII", 2, size_w, size_h, 17, 0, 0)
    body = b"".join(struct.pack("<HB", TILE_ID, 0) for _ in range(cells))
    with open(os.path.join(folder, "map.bin"), "wb") as f:
        f.write(header + body)

    actors = []
    for i, (name, owner, x, y, facing) in enumerate(placed):
        actors.append(f"\tActor{i}: {name}\n\t\tOwner: {owner}\n\t\tLocation: {x},{y}\n\t\tFacing: {facing}\n")

    yaml = f"""MapFormat: 12

RequiresMod: tgmc

Title: {title}

Author: local smoke test

Tileset: TGMC

MapSize: {size_w},{size_h}

Bounds: 0,0,{size_w},{size_h}

Visibility: {visibility}

Categories: Skirmish

Players:
	PlayerReference@Neutral:
		Name: Neutral
		OwnsWorld: True
		NonCombatant: True
	PlayerReference@Marines:
		Name: Marines
		Playable: True
		Faction: marines
	PlayerReference@Xenos:
		Name: Xenos
		Playable: True
		Faction: xenos

Actors:
{"".join(actors)}"""
    with open(os.path.join(folder, "map.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(yaml)

    preview = Image.new("RGBA", (size_w, size_h), (0x3B, 0x5A, 0x2F, 255))
    preview.save(os.path.join(folder, "map.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    write_palette(os.path.join(args.out, "tgmc.pal"))
    write_ground_tile(os.path.join(args.out, "ground.png"))
    write_cursor(os.path.join(args.out, "cursor.png"))
    write_clock(os.path.join(args.out, "clock.png"))
    write_map(os.path.join(args.out, "maps", "test-field"), "TGMC test field", 24, 24, TEST_FIELD, "Lobby, Shellmap")
    write_map(os.path.join(args.out, "maps", "landing-zone"), "Landing Zone", 40, 28, LANDING_ZONE, "Lobby")
    print(f"placeholders written to {args.out}")


if __name__ == "__main__":
    main()
