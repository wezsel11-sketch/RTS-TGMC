"""Generate the non-TGMC pieces the mod needs to load and show a test field.

Nothing here is TGMC art. It writes:
  tgmc.pal                      a flat grey 256-colour palette (OpenRA needs one for its palette setup)
  ground.png                    one 24x24 green ground tile for the terrain template
  cursor.png                    a plain arrow for the default cursor
  maps/test-field/map.{yaml,bin,png}   a 24x24 map with marines, runners, and one of each structure

Usage: make_placeholders.py --out DIR
"""
import argparse
import os
import struct

from PIL import Image, PngImagePlugin

MAP_SIZE = 24
TILE_ID = 1  # Template@1 in tilesets/ground.yaml, which is the Clear ground tile

# (actor, owner, x, y, facing). Facing is in OpenRA angle units: 0 = north, 512 = south.
ACTORS = [
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


def write_map(folder):
    os.makedirs(folder, exist_ok=True)
    cells = MAP_SIZE * MAP_SIZE
    # map.bin: version byte, width, height, u32 tiles offset, u32 heights offset (0), u32 resources offset (0),
    # then per cell (x-major): u16 template id, u8 variant index.
    header = struct.pack("<BHHIII", 2, MAP_SIZE, MAP_SIZE, 17, 0, 0)
    body = b"".join(struct.pack("<HB", TILE_ID, 0) for _ in range(cells))
    with open(os.path.join(folder, "map.bin"), "wb") as f:
        f.write(header + body)

    actors = []
    for i, (name, owner, x, y, facing) in enumerate(ACTORS):
        actors.append(f"\tActor{i}: {name}\n\t\tOwner: {owner}\n\t\tLocation: {x},{y}\n\t\tFacing: {facing}\n")

    yaml = f"""MapFormat: 12

RequiresMod: tgmc

Title: TGMC test field

Author: local smoke test

Tileset: TGMC

MapSize: {MAP_SIZE},{MAP_SIZE}

Bounds: 0,0,{MAP_SIZE},{MAP_SIZE}

Visibility: Lobby, Shellmap

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

    preview = Image.new("RGBA", (MAP_SIZE, MAP_SIZE), (0x3B, 0x5A, 0x2F, 255))
    preview.save(os.path.join(folder, "map.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    write_palette(os.path.join(args.out, "tgmc.pal"))
    write_ground_tile(os.path.join(args.out, "ground.png"))
    write_cursor(os.path.join(args.out, "cursor.png"))
    write_map(os.path.join(args.out, "maps", "test-field"))
    print(f"placeholders written to {args.out}")


if __name__ == "__main__":
    main()
