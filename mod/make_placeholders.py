"""Generate the non-TGMC pieces the mod needs to load and show a test field.

Nothing here is TGMC art. It writes:
  tgmc.pal                      a flat grey 256-colour palette (OpenRA needs one for its palette setup)
  cursor.png                    a plain arrow for the default cursor
  shroud.png, fog.png           14 edge tiles each for unexplored and out-of-sight cells; shroudfull.png and fogfull.png
  rally-flag.png, rally-circles.png  the rally point marker: a waving flag and pulsing ground rings
  clock.png                     production-icon clock overlay frames (62x46, a dark wedge that sweeps away)
  moveflsh.png                  the move-order click effect: a 4-frame ring that grows and fades (32x32)
  cas-icon.png                  the CAS strike's support power icon (62x46)
  maps/test-field/map.{yaml,bin,png}   a 24x24 map with marines, runners, and one of each structure
  maps/landing-zone/map.{yaml,bin,png} a 40x28 two-base skirmish map: marines west, xenos east
  maps/hold-the-line/...        the survival map; its script list ends with tgmc|scripts/music.lua

Usage: make_placeholders.py --out DIR
"""
import argparse
import math
import os
import re
import shutil
import struct
import sys

from PIL import Image, ImageDraw, PngImagePlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_sounds  # noqa: E402
import tgmc_dmm  # noqa: E402

CLOCK_W, CLOCK_H, CLOCK_FRAMES, CLOCK_COLS = 62, 46, 30, 6  # matches the sidebar palette's IconSize
# Template ids in tilesets/ground.yaml. Grass lists two images, which the engine picks between per cell. The byte
# after the id in map.bin is the tile's index within a multi-cell template, so it is 0 for every one of these.
GRASS, WATER, FORD, DIRT, ROCK = 1, 2, 3, 4, 5

# (actor, owner, x, y, facing). Facing is in OpenRA angle units: 0 = north, 512 = south.
TEST_FIELD = [
    ("rifleman", "Marines", 9, 11, 0),
    ("rifleman", "Marines", 10, 11, 256),
    ("rifleman", "Marines", 11, 11, 512),
    ("runner", "Xenos", 13, 12, 0),
    ("runner", "Xenos", 14, 12, 256),
    ("runner", "Xenos", 15, 12, 512),
    ("hunter", "Xenos", 13, 14, 256),
    ("sentinel", "Xenos", 14, 14, 256),
    ("drone", "Xenos", 15, 14, 256),
    ("queen", "Xenos", 16, 12, 256),
    ("resin-turret", "Xenos", 17, 10, 0),
    ("resin-silo", "Xenos", 4, 4, 0),
    ("mini-silo", "Xenos", 18, 4, 0),
    ("medic", "Marines", 9, 13, 512),
    ("engineer", "Marines", 10, 13, 512),
    ("sentry-turret", "Marines", 12, 8, 512),
    ("cryo-pod", "Marines", 5, 17, 512),
    ("vendor", "Marines", 19, 17, 512),
    ("smartgunner", "Marines", 7, 14, 512),
    ("grenadier", "Marines", 8, 16, 512),
    ("warrior", "Xenos", 20, 12, 0),
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
    ("hunter", "Xenos", 30, 14, 768),
    ("sentinel", "Xenos", 31, 13, 768),
    ("drone", "Xenos", 32, 16, 768),
    ("queen", "Xenos", 32, 14, 768),
]


def flat_ground(x, y):
    return GRASS, 0


def landing_zone_ground(x, y):
    """A two-cell river down the middle with three fords, and a dirt road linking the two bases."""
    if x in (19, 20):
        return (FORD, 0) if y in (4, 5, 12, 13, 14, 15, 22, 23) else (WATER, 0)
    if y == 13 and (6 <= x <= 32):
        return DIRT, 0
    return flat_ground(x, y)


def _ellipse(x, y, cx, cy, rx, ry):
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def _road(x, y, row, x0, x1):
    return y == row and x0 <= x <= x1


def canyon_run_ground(x, y):
    """52x28. Water walls leave a six-wide lane down the middle and two two-wide trails along the edges: one choke, two flanks."""
    if 15 <= x <= 36:
        if 11 <= y <= 16:
            return (DIRT if y in (13, 14) else GRASS), 0
        return (GRASS, 0) if y in (3, 4, 23, 24) else (WATER, 0)
    return (DIRT, 0) if _road(x, y, 13, 6, 45) else (GRASS, 0)


def jungle_crossing_ground(x, y):
    """44x28. A lake in the middle: go round it by the north or south shore, or wade the causeway through the centre."""
    if _ellipse(x, y, 22, 13.5, 7, 9):
        return (FORD, 0) if y in (13, 14) else (WATER, 0)
    if any(_ellipse(x, y, cx, cy, 2, 2) for cx, cy in ((12, 5), (12, 22), (32, 5), (32, 22))):
        return WATER, 0
    return (DIRT, 0) if _road(x, y, 13, 6, 38) else (GRASS, 0)


def close_quarters_ground(x, y):
    """34x28. The bases are 13 cells apart, split by a thin river with fords. The xenos' fast rush has little ground to cross."""
    if x in (16, 17):
        return (FORD, 0) if y in (3, 4, 12, 13, 14, 15, 23, 24) else (WATER, 0)
    if any(_ellipse(x, y, cx, cy, 2, 3) for cx, cy in ((13, 7), (20, 20), (13, 21), (20, 6))):
        return WATER, 0
    return (DIRT, 0) if _road(x, y, 13, 6, 27) else (GRASS, 0)


def great_plains_ground(x, y):
    """64x40. Open grass and scattered ponds; a long walk, so tech and walls matter more than a first rush."""
    ponds = ((20, 12, 3, 3), (28, 26, 4, 3), (32, 19, 3, 2), (38, 10, 3, 3), (42, 28, 3, 3), (24, 32, 2, 2), (46, 18, 2, 3))
    if any(_ellipse(x, y, *pond) for pond in ponds):
        return WATER, 0
    return (DIRT, 0) if _road(x, y, 19, 6, 58) or (x == 32 and 4 <= y <= 36 and not _ellipse(x, y, 32, 19, 3, 2)) else (GRASS, 0)


def palette_entries():
    """A plain grey ramp. Only the palette-based paths read it; the TGMC-free tiles and sprites are RGBA."""
    return [(i, i, i) for i in range(256)]


def write_palette(path):
    with open(path, "wb") as f:
        f.write(bytes(c for rgb in palette_entries() for c in rgb))


def write_cursor(path):
    """A plain arrow, drawn here so the mod has a cursor without any TGMC art."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y in range(12):
        for x in range(min(y + 1, 8)):
            px[x, y] = (255, 255, 255, 255) if x == 0 or x == y or y == 11 else (0, 0, 0, 255)
    img.save(path)


def write_shroud_tiles(out, tile=32):
    """Edge tiles for ShroudRenderer. Frame i - 1 darkens the quadrants named by the bits of i (1 TL, 2 TR, 4 BR, 8 BL).

    Each quadrant's darkness is a value at its centre, bilinearly blended across the tile, so the edge fades over
    about half a tile instead of stepping at the quadrant border.
    """
    half = tile // 2
    centres = {1: (half / 2, half / 2), 2: (half + half / 2, half / 2), 4: (half + half / 2, half + half / 2), 8: (half / 2, half + half / 2)}
    for name, alpha in (("shroud", 255), ("fog", 128)):
        sheet = Image.new("RGBA", (tile * 14, tile), (0, 0, 0, 0))
        px = sheet.load()
        for pattern in range(1, 15):
            # Quadrant darkness at each centre, in TL, TR, BR, BL order
            corners = [1.0 if pattern & bit else 0.0 for bit in (1, 2, 4, 8)]
            for y in range(tile):
                for x in range(tile):
                    # Bilinear blend of the four centres, clamped to the tile
                    u = min(max((x + 0.5 - centres[1][0]) / half, 0.0), 1.0)
                    v = min(max((y + 0.5 - centres[1][1]) / half, 0.0), 1.0)
                    top = corners[0] * (1 - u) + corners[1] * u
                    bottom = corners[3] * (1 - u) + corners[2] * u
                    a = int(round(alpha * (top * (1 - v) + bottom * v)))
                    px[tile * (pattern - 1) + x, y] = (0, 0, 0, a)
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", f"{tile},{tile}")
        meta.add_text("FrameAmount", "14")
        sheet.save(os.path.join(out, f"{name}.png"), pnginfo=meta)

        full = Image.new("RGBA", (tile, tile), (0, 0, 0, alpha))
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", f"{tile},{tile}")
        meta.add_text("FrameAmount", "1")
        full.save(os.path.join(out, f"{name}full.png"), pnginfo=meta)


def write_rally_marker(out):
    """A 4-frame waving flag (16x24) and 4 pulsing ground rings (32x24), tinted by the player palette's colour."""
    flag = Image.new("RGBA", (16 * 4, 24), (0, 0, 0, 0))
    for i in range(4):
        d = ImageDraw.Draw(flag)
        x = 16 * i
        d.line([(x + 3, 2), (x + 3, 22)], fill=(200, 200, 200, 255), width=2)
        wave = (0, 1, 0, -1)[i]
        d.polygon([(x + 5, 3), (x + 14, 6 + wave), (x + 5, 10)], fill=(209, 154, 43, 255), outline=(40, 30, 10, 255))
    circles = Image.new("RGBA", (32 * 4, 24), (0, 0, 0, 0))
    for i in range(4):
        d = ImageDraw.Draw(circles)
        r = 4 + 3 * i
        d.ellipse([32 * i + 16 - r, 12 - r // 2 - 1, 32 * i + 16 + r, 12 + r // 2 + 1], outline=(209, 154, 43, 255 - 50 * i), width=1)
    for name, img, size in (("rally-flag", flag, "16,24"), ("rally-circles", circles, "32,24")):
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", size)
        meta.add_text("FrameAmount", "4")
        img.save(os.path.join(out, f"{name}.png"), pnginfo=meta)


def write_move_flash(out):
    """A 4-frame white ring (32x32) that grows and fades: OpenRA's terrain flash on a move order (no TGMC art)."""
    img = Image.new("RGBA", (32 * 4, 32), (0, 0, 0, 0))
    for i in range(4):
        d = ImageDraw.Draw(img)
        r = 5 + 3 * i
        d.ellipse([32 * i + 16 - r, 16 - r, 32 * i + 16 + r, 16 + r], outline=(255, 255, 255, 230 - 50 * i), width=2)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", "32,32")
    meta.add_text("FrameAmount", "4")
    img.save(os.path.join(out, "moveflsh.png"), pnginfo=meta)


CAS_ICONS = ["cas", "gun", "minirocket", "flare", "widowmaker", "laser", "napalm", "fatty", "moab"]


def write_cas_icon(out):
    """The palette icons for the CAS ammo types (62x46 each, one row of frames in CAS_ICONS order): a card with a small drawing
    of the ammo and its short name. No TGMC art."""
    w, h = 62, 46
    img = Image.new("RGBA", (w * len(CAS_ICONS), h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    red, amber, white, cyan = (240, 90, 50, 255), (255, 170, 40, 255), (240, 240, 230, 255), (90, 220, 255, 255)
    labels = ["BOMBS", "30MM", "MINI", "FLARE", "AGM", "LASER", "NAPALM", "FATTY", "MOAB"]
    for i, name in enumerate(CAS_ICONS):
        ox = w * i
        d.rectangle([ox, 0, ox + w - 1, h - 1], fill=(24, 26, 30, 255), outline=(90, 96, 104, 255))
        cx, cy = ox + 31, 19
        if name == "cas":
            for dx in (-16, -8, 0, 8, 16):
                d.ellipse([cx + dx - 3, cy - 3, cx + dx + 3, cy + 3], fill=red)
        elif name == "gun":
            for dx in range(-18, 19, 6):
                d.line([cx + dx, cy - 6, cx + dx, cy + 6], fill=amber, width=2)
        elif name == "minirocket":
            for dx in (-14, 0, 14):
                d.polygon([(cx + dx, cy - 9), (cx + dx - 3, cy + 5), (cx + dx + 3, cy + 5)], fill=amber)
        elif name == "flare":
            d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=white)
            for dx, dy in ((-12, 0), (12, 0), (0, -10), (0, 10), (-9, -8), (9, 8), (-9, 8), (9, -8)):
                d.line([cx + dx // 2, cy + dy // 2, cx + dx, cy + dy], fill=white, width=1)
        elif name == "widowmaker":
            d.polygon([(cx, cy - 11), (cx - 5, cy + 7), (cx + 5, cy + 7)], fill=red)
            d.line([cx, cy + 7, cx, cy + 13], fill=amber, width=2)
        elif name == "laser":
            d.line([cx - 22, cy + 6, cx + 22, cy - 6], fill=cyan, width=3)
            d.line([cx - 22, cy + 6, cx + 22, cy - 6], fill=white, width=1)
        elif name == "napalm":
            d.polygon([(cx, cy - 12), (cx - 9, cy + 8), (cx, cy + 4), (cx + 9, cy + 8)], fill=(255, 120, 20, 255))
            d.polygon([(cx, cy - 4), (cx - 4, cy + 8), (cx + 4, cy + 8)], fill=amber)
        elif name == "fatty":
            d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=red)
            for k in range(8):
                import math
                a = k * math.pi / 4
                d.ellipse([cx + 14 * math.cos(a) - 2, cy + 11 * math.sin(a) - 2, cx + 14 * math.cos(a) + 2, cy + 11 * math.sin(a) + 2], fill=amber)
        elif name == "moab":
            d.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=red)
            d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=amber)
            d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=white)
        d.text((ox + 31 - 3 * len(labels[i]), 33), labels[i], fill=white)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{w},{h}")
    meta.add_text("FrameAmount", str(len(CAS_ICONS)))
    img.save(os.path.join(out, "cas-icon.png"), pnginfo=meta)


HIVE_ICONS = ["cure", "burrowed", "rage"]


def write_hive_icon(out):
    """The palette icons for the hive powers (62x46 each, in HIVE_ICONS order): a card with a small drawing and a short name. No TGMC art."""
    w, h = 62, 46
    img = Image.new("RGBA", (w * len(HIVE_ICONS), h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    green, red, amber, white = (110, 230, 90, 255), (240, 70, 60, 255), (255, 170, 40, 255), (240, 240, 230, 255)
    labels = ["CURE", "BURROW", "RAGE"]
    for i, name in enumerate(HIVE_ICONS):
        ox = w * i
        d.rectangle([ox, 0, ox + w - 1, h - 1], fill=(22, 28, 24, 255), outline=(90, 110, 96, 255))
        cx, cy = ox + 31, 19
        if name == "cure":
            d.rectangle([cx - 3, cy - 11, cx + 3, cy + 11], fill=green)
            d.rectangle([cx - 11, cy - 3, cx + 11, cy + 3], fill=green)
        elif name == "burrowed":
            d.ellipse([cx - 16, cy + 3, cx + 16, cy + 12], fill=(70, 50, 36, 255))
            for dx in (-9, 0, 9):
                d.polygon([(cx + dx, cy - 10), (cx + dx - 4, cy + 5), (cx + dx + 4, cy + 5)], fill=amber)
        elif name == "rage":
            for dx in (-8, 0, 8):
                d.polygon([(cx + dx, cy - 12), (cx + dx - 3, cy + 10), (cx + dx + 3, cy + 10)], fill=red)
            d.line([cx - 14, cy + 11, cx + 14, cy + 11], fill=amber, width=2)
        d.text((ox + 31 - 3 * len(labels[i]), 33), labels[i], fill=white)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{w},{h}")
    meta.add_text("FrameAmount", str(len(HIVE_ICONS)))
    img.save(os.path.join(out, "hive-icon.png"), pnginfo=meta)


LIGHT_COLOURS = {"warm": (255, 170, 70), "white": (255, 235, 170), "green": (120, 255, 90), "fire": (255, 110, 30), "acidloop": (120, 255, 90)}


def write_lights(out):
    """Soft round glows for lighting effects (muzzle flashes, blasts, acid, fire), 128x128, six frames each that fade from bright to nothing
    (the fire one flickers instead). They are drawn over the ground with additive blending (see fx-light in sequences/misc.yaml), so
    they brighten what is under them. One sheet per colour. No TGMC art."""
    import math
    size, frames = 128, 6
    for name, rgb in LIGHT_COLOURS.items():
        img = Image.new("RGBA", (size * frames, size), (0, 0, 0, 0))
        px = img.load()
        for f in range(frames):
            if name in ("fire", "acidloop"):
                level = (1.0, 0.8, 0.95, 0.7, 1.0, 0.85)[f]
            else:
                level = (1.0 - f / frames) ** 1.5
            for y in range(size):
                for x in range(size):
                    r = math.hypot(x - size / 2 + 0.5, y - size / 2 + 0.5) / (size / 2)
                    if r >= 1:
                        continue
                    a = (1 - r) ** 2.2 * level * 0.55
                    px[size * f + x, y] = rgb + (int(255 * a),)
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", f"{size},{size}")
        meta.add_text("FrameAmount", str(frames))
        img.save(os.path.join(out, f"light-{name}.png"), pnginfo=meta)


def write_overlay(out):
    """The building ghost's cell tiles: frame 0 is a green translucent tile for a cell the building may use, frame 1 a red one for a
    blocked cell. The engine's placement preview asks for the image `overlay`, sequences build-valid and build-invalid."""
    img = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, rgb in enumerate(((60, 230, 90), (235, 60, 50))):
        d.rectangle([32 * i, 0, 32 * i + 31, 31], fill=rgb + (95,), outline=rgb + (230,), width=1)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", "32,32")
    meta.add_text("FrameAmount", "2")
    img.save(os.path.join(out, "overlay.png"), pnginfo=meta)


def write_acid_pool(out):
    """The puddle a dead xeno leaves: 4 frames of a green blob that swells and shrinks, 32x32 (made here, not from TGMC)."""
    frames = 4
    img = Image.new("RGBA", (32 * frames, 32), (0, 0, 0, 0))
    for i in range(frames):
        layer = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        r = 10 + (i if i < 3 else 1)
        d.ellipse([16 - r, 17 - r // 2 - 1, 16 + r, 17 + r // 2 + 1], fill=(70, 200, 60, 150), outline=(150, 255, 90, 210))
        d.ellipse([16 - r // 2, 17 - r // 4, 16 + r // 3, 17 + r // 4], fill=(150, 255, 90, 120))
        img.paste(layer, (32 * i, 0))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", "32,32")
    meta.add_text("FrameAmount", str(frames))
    img.save(os.path.join(out, "acid-pool.png"), pnginfo=meta)


def write_repair_fx(out):
    """Medic and engineer signals, drawn here rather than from TGMC: 8 frames each, 24x24.

    heal-plus.png: three green crosses that rise and fade, for a heal. repair-wrench.png: a steel wrench that rocks on a
    pivot, with sparks at the jaw, for a repair on a machine or a building.
    """
    size, frames = 24, 8
    plus_green, plus_dark = (120, 230, 100, 255), (20, 60, 20, 255)

    # Heals get a wider 32 px frame so three crosses 10 px apart fit with room between them
    hsize = 32
    heal = Image.new("RGBA", (hsize * frames, hsize), (0, 0, 0, 0))
    for i in range(frames):
        frame = Image.new("RGBA", (hsize, hsize), (0, 0, 0, 0))
        d = ImageDraw.Draw(frame)
        rise = int(i * 1.5)
        alpha = 255 if i < frames - 2 else 120
        # each cross is 7x7 (2 px arms) with a 1 px dark outline; the middle one sits a little higher
        for cx, lift in ((6, 0), (16, 3), (26, 0)):
            cy = 26 - rise - lift
            for off, fill in ((1, plus_dark), (0, plus_green[:3] + (alpha,))):
                d.rectangle([cx - 3 - off, cy - 1 - off, cx + 3 + off, cy + 1 + off], fill=fill)
                d.rectangle([cx - 1 - off, cy - 3 - off, cx + 1 + off, cy + 3 + off], fill=fill)
        heal.paste(frame, (hsize * i, 0))

    steel, steel_dark, spark = (190, 196, 204, 255), (40, 42, 48, 255), (255, 220, 80, 255)
    # The wrench is drawn once, upright, then turned by each frame's angle about the sheet's centre.
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    d.line([(9, 21), (15, 13)], fill=steel_dark, width=5)  # handle outline
    d.line([(9, 21), (15, 13)], fill=steel, width=3)
    d.ellipse([9, 2, 21, 14], fill=steel_dark)  # jaw outline
    d.ellipse([10, 3, 20, 13], fill=steel)
    d.rectangle([14, 4, 19, 8], fill=(0, 0, 0, 0))  # the open jaw
    angles = (-30, -15, 0, 15, 30, 15, 0, -15)
    wrench = Image.new("RGBA", (size * frames, size), (0, 0, 0, 0))
    for i, angle in enumerate(angles):
        frame = base.rotate(angle, resample=Image.BICUBIC, center=(size / 2, size / 2))
        if i in (1, 2, 3, 4, 5):
            # short rays from the jaw, three of the five directions per frame so the sparks flicker
            sd = ImageDraw.Draw(frame)
            jaw = (13, 6)
            rays = ((-1, -1), (1, -1), (2, 0), (1, 1), (-1, 1))
            for dx, dy in (rays[(i + k) % len(rays)] for k in range(3)):
                sd.line([jaw, (jaw[0] + 3 * dx, jaw[1] + 3 * dy)], fill=spark, width=1)
        wrench.paste(frame, (size * i, 0), frame)

    for name, img, fs in (("heal-plus", heal, hsize), ("repair-wrench", wrench, size)):
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", f"{fs},{fs}")
        meta.add_text("FrameAmount", str(frames))
        img.save(os.path.join(out, f"{name}.png"), pnginfo=meta)


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


# Scenario maps for mod/test_scenarios.sh. Each runs a Lua script from mod/scenarios, copied into the map folder
# (the map lint only accepts scripts inside the map), that prints a PASS or FAIL line.
# A far-off xeno silo keeps the game from ending at tick zero, where it is not part of the test.
def _scenario(script, marines):
    return {"scripts": (script,), "actors": marines + [("resin-silo", "Xenos", 19, 19, 0)]}


# Hold the Line: the marine half of Landing Zone. The xeno waves come from the east edge.
HOLD_THE_LINE = [a for a in LANDING_ZONE if a[1] == "Marines"] + [
    ("sentry-turret", "Marines", 11, 13, 256),
    ("rifleman", "Marines", 8, 15, 256),
    ("rifleman", "Marines", 8, 11, 256),
]

def _skirmish_actors(xeno_dx, dy):
    """Landing Zone's two bases, the xeno one moved by xeno_dx and both by dy."""
    return [(n, o, x + (xeno_dx if o == "Xenos" else 0), y + dy, f) for n, o, x, y, f in LANDING_ZONE]


# name: (title, width, height, xeno base shift, vertical shift of both bases, ground). Marines west, xenos east, like Landing Zone.
SKIRMISH_MAPS = {
    "canyon-run": ("Canyon Run", 52, 28, 12, 0, canyon_run_ground),
    "jungle-crossing": ("Jungle Crossing", 44, 28, 4, 0, jungle_crossing_ground),
    "close-quarters": ("Close Quarters", 34, 28, -6, 0, close_quarters_ground),
    "great-plains": ("Great Plains", 64, 40, 24, 6, great_plains_ground),
}

SCENARIOS = {
    "scenario-heal": _scenario("test-heal", [
        ("medic", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 9, 12, 512),
        ("rifleman", "Marines", 10, 12, 512),
        ("rifleman", "Marines", 11, 12, 512),
    ]),
    "scenario-repair": _scenario("test-repair", [
        ("engineer", "Marines", 10, 10, 512),
        ("sentry-turret", "Marines", 10, 12, 512),
    ]),
    "scenario-combat": _scenario("test-combat", [
        ("rifleman", "Marines", 10, 10, 512),
        ("runner", "Xenos", 13, 10, 0),
    ]),
    "scenario-mend": {"scripts": ("test-mend",), "actors": [
        ("drone", "Xenos", 10, 10, 512),
        ("resin-turret", "Xenos", 10, 12, 512),
        ("rifleman", "Marines", 20, 20, 0),
    ]},
    "scenario-waves": {"scripts": ("wave-survival", "test-waves"), "drop_conquest": True, "actors": [
        ("rifleman", "Marines", 9, 10, 512),
        ("rifleman", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 11, 10, 512),
        ("rifleman", "Marines", 9, 12, 512),
        ("rifleman", "Marines", 10, 12, 512),
    ]},
    "scenario-ai": {"scripts": ("test-ai",), "xeno_bot": "skirmish", "actors": [
        ("rifleman", "Marines", 3, 3, 512),
        ("resin-silo", "Xenos", 16, 16, 0),
    ]},
    "scenario-ai-mix": {"scripts": ("test-ai-mix",), "xeno_bot": "skirmish", "size": (48, 48), "spawns": [(4, 4), (40, 40)], "actors": [
        ("rifleman", "Marines", 4, 4, 512),
        ("resin-silo", "Xenos", 40, 40, 0),
    ]},
    # Both bots left alone with plenty of cash and no squads: do they build the Forward Hive, Resin Traps, Mortar and Artillery
    # Emplacements and the Workshop, and train the heavy castes and weapons (see scenarios/test-ai-expand.lua)?
    "scenario-ai-expand": {"scripts": ("test-ai-expand",), "xeno_bot": "skirmish", "marine_bot": "skirmish", "fast": True,
                           "size": (64, 64), "spawns": [(8, 8), (55, 55)],
                           "extra_rules": "Player:\n\t-SquadManagerBotModule@marines-easy:\n\t-SquadManagerBotModule@marines-normal:\n\t-SquadManagerBotModule@marines-hard:\n\t-SquadManagerBotModule@xenos-easy:\n\t-SquadManagerBotModule@xenos-normal:\n\t-SquadManagerBotModule@xenos-hard:\n", "actors": [
        ("cryo-pod", "Marines", 8, 8, 0),
        ("rifleman", "Marines", 10, 10, 512),
        ("resin-silo", "Xenos", 55, 55, 0),
    ]},
    # The tech tree and the Miner and Weed Node income (see scenarios/test-build.lua). The xeno side has a queen and a silo.
    "scenario-build": {"scripts": ("test-build",), "actors": [
        ("engineer", "Marines", 10, 10, 512),
        ("cryo-pod", "Marines", 6, 6, 0),
        ("queen", "Xenos", 20, 16, 0),
        ("resin-silo", "Xenos", 16, 16, 0),
    ]},
    # Infestation and evolving (see scenarios/test-infest.lua, test-infest-cure.lua, test-evolve.lua, test-weeds.lua).
    # A spare marine far away keeps the xenos from winning when the host dies. The burst timer is cut from a minute to 12 seconds
    # so the run is short.
    "scenario-infest": {"scripts": ("test-infest",), "extra_rules": "^Infantry:\n\tInfestable:\n\t\tBurstDelay: 300\n\t\tHugDuration: 60\n", "actors": [
        ("rifleman", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 20, 20, 0),
        ("facehugger", "Xenos", 12, 10, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    # Explosives, heavy marines and the pounce (see scenarios/test-explosive.lua, test-heavy.lua, test-pounce.lua).
    "scenario-egg": {"scripts": ("test-egg",), "actors": [
        ("egg", "Xenos", 10, 10, 0),
        ("rifleman", "Marines", 12, 10, 512),
        ("rifleman", "Marines", 20, 20, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-mature": {"scripts": ("test-mature",), "extra_rules": "^Xeno:\n\tMaturity:\n\t\tTicks: 60, 120, 180\n\t\tPrerequisite:\n", "actors": [
        ("runner", "Xenos", 10, 10, 0),
        ("rifleman", "Marines", 20, 20, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-explosive": {"scripts": ("test-explosive",), "actors": [
        ("demolitionist", "Marines", 10, 10, 512),
        ("demolitionist", "Marines", 15, 11, 512),
        ("rifleman", "Marines", 15, 9, 512),
        ("crusher", "Xenos", 15, 10, 0),
        ("rifleman", "Marines", 20, 20, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-nofriendlyfire": {"scripts": ("test-nofriendlyfire",), "extra_rules": "World:\n\tTgmcOptions:\n\t\tFriendlyFireDefault: false\n", "actors": [
        ("demolitionist", "Marines", 10, 10, 512),
        ("demolitionist", "Marines", 15, 11, 512),
        ("rifleman", "Marines", 15, 9, 512),
        ("crusher", "Xenos", 15, 10, 0),
        ("rifleman", "Marines", 20, 20, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-medbay": {"scripts": ("test-medbay",), "actors": [
        ("medbay", "Marines", 10, 10, 0),
        ("rifleman", "Marines", 12, 10, 512),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-pylon": {"scripts": ("test-pylon",), "actors": [
        ("recovery-pylon", "Xenos", 10, 10, 0),
        ("runner", "Xenos", 13, 10, 0),
        ("rifleman", "Marines", 20, 20, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-mech": {"scripts": ("test-mech",), "actors": [
        ("mech", "Marines", 10, 10, 512),
        ("hunter", "Xenos", 15, 9, 0),
        ("hunter", "Xenos", 15, 11, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-cas-ammo": {"scripts": ("test-cas-ammo",), "size": (88, 48), "spawns": [(6, 40), (84, 44)], "actors": [
        ("ordnance-depot", "Marines", 6, 6, 0),
        ("workshop", "Marines", 10, 6, 0),
        ("hunter", "Xenos", 8, 30, 0),
        ("hunter", "Xenos", 16, 30, 0),
        ("hunter", "Xenos", 24, 30, 0),
        ("hunter", "Xenos", 32, 30, 0),
        ("hunter", "Xenos", 40, 30, 0),
        ("hunter", "Xenos", 48, 30, 0),
        ("hunter", "Xenos", 56, 30, 0),
        ("hunter", "Xenos", 64, 30, 0),
        ("hunter", "Xenos", 72, 30, 0),
        ("rifleman", "Marines", 5, 40, 0),
        ("resin-silo", "Xenos", 84, 44, 0),
    ]},
    "scenario-cas": {"scripts": ("test-cas",), "actors": [
        ("ordnance-depot", "Marines", 6, 6, 0),
        ("rifleman", "Marines", 14, 10, 512),
        ("rifleman", "Marines", 20, 20, 0),
        ("hunter", "Xenos", 15, 10, 0),
        ("hunter", "Xenos", 16, 11, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    # Not a test: selects some units and takes a screenshot, to look at the HUD (see ScreenshotAtInfo in tgmc/code/Hud.cs).
    "shot-hud": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 120\n\t\tSelect: rifleman, heavygunner, mech, ordnance-depot\n", "actors": [
        ("ordnance-depot", "Marines", 11, 7, 0),
        ("rifleman", "Marines", 10, 10, 512),
        ("heavygunner", "Marines", 12, 10, 512),
        ("mech", "Marines", 14, 11, 512),
        ("medbay", "Marines", 8, 8, 0),
        ("hunter", "Xenos", 18, 12, 0),
        ("egg", "Xenos", 20, 10, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "shot-cas": {"scripts": ("test-cas",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 190\n\t\tSelect: mech\n", "actors": [
        ("ordnance-depot", "Marines", 6, 6, 0),
        ("rifleman", "Marines", 14, 10, 512),
        ("rifleman", "Marines", 20, 20, 0),
        ("mech", "Marines", 11, 13, 512),
        ("hunter", "Xenos", 15, 10, 0),
        ("hunter", "Xenos", 16, 11, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "shot-napalm": {"scripts": ("shot-napalm",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 215\n", "actors": [
        ("ordnance-depot", "Marines", 6, 6, 0),
        ("workshop", "Marines", 8, 6, 0),
        ("rifleman", "Marines", 20, 20, 0),
        ("hunter", "Xenos", 15, 12, 0),
        ("hunter", "Xenos", 17, 13, 0),
        ("hunter", "Xenos", 14, 14, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "shot-ghost": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 60\n\t\tPlace: medbay\n", "actors": [
        ("armory", "Marines", 10, 10, 0),
        ("rifleman", "Marines", 12, 12, 512),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "shot-lr": {"scripts": ("shot-lr",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 70\n", "actors": [
        ("rifleman", "Marines", 10, 6, 0), ("hunter", "Xenos", 5, 6, 0),
        ("rifleman", "Marines", 10, 9, 0), ("hunter", "Xenos", 15, 9, 0),
        ("sniper", "Marines", 10, 12, 0), ("hunter", "Xenos", 5, 12, 0),
        ("rocketeer", "Marines", 10, 15, 0), ("hunter", "Xenos", 15, 15, 0),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    "shot-jet": {"scripts": ("shot-jet",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 112\n", "actors": [
        ("ordnance-depot", "Marines", 6, 6, 0),
        ("rifleman", "Marines", 12, 9, 0),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    "shot-corpse": {"scripts": ("shot-corpse",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 160\n", "actors": [
        ("rifleman", "Marines", 10, 8, 0), ("rifleman", "Marines", 12, 8, 256),
        ("hunter", "Xenos", 10, 11, 0), ("hunter", "Xenos", 12, 11, 0),
        ("medic", "Marines", 7, 7, 0),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    "shot-cades": {"scripts": ("shot",), "drop_conquest": True, "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 40\n", "actors": [
        ("cryo-pod", "Marines", 12, 12, 0),
        ("cade", "Marines", 12, 9, 0), ("cade", "Marines", 12, 15, 0), ("cade", "Marines", 9, 12, 0), ("cade", "Marines", 15, 12, 0),
        ("rifleman", "Marines", 11, 11, 512), ("medic", "Marines", 13, 11, 512), ("engineer", "Marines", 11, 13, 512),
        ("flamer", "Marines", 18, 14, 256), ("crusher", "Xenos", 22, 14, 0), ("resin-silo", "Xenos", 22, 22, 0),
        ("mortar-emplacement", "Marines", 6, 18, 0), ("artillery-emplacement", "Marines", 9, 18, 0),
    ]},
    # Not a test: screenshot of the lighting glows around a fire, a pool of acid and a gas cloud (see scenarios/shot-lights.lua).
    "shot-lights": {"scripts": ("shot-lights",), "size": (40, 24), "drop_conquest": True, "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 40\n", "actors": [
        ("flame-patch", "Marines", 14, 12, 0), ("acid-pool", "Xenos", 20, 12, 0), ("gas-cloud", "Xenos", 26, 12, 0),
        ("rifleman", "Marines", 16, 14, 0), ("hunter", "Xenos", 24, 14, 0), ("resin-silo", "Xenos", 36, 20, 0),
    ]},
    # Not a test: screenshot a moment after a howitzer shell lands, to see the blast flash (see BlastFlash in tgmc/code/Lights.cs).
    "shot-flash": {"scripts": ("shot-flash",), "size": (48, 32), "drop_conquest": True, "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 110\n", "actors": [
        ("artillery-emplacement", "Marines", 6, 12, 0), ("rifleman", "Marines", 20, 12, 0),
        ("crusher", "Xenos", 24, 12, 0), ("resin-silo", "Xenos", 40, 28, 0),
    ]},
    # The Jaeger marines side by side, each three cells from a crusher (see scenarios/test-jaeger.lua).
    "scenario-jaeger": {"scripts": ("test-jaeger",), "size": (24, 32), "drop_conquest": True, "actors": [
        ("scout", "Marines", 8, 6, 256), ("crusher", "Xenos", 11, 6, 768),
        ("skirmisher", "Marines", 8, 10, 256), ("crusher", "Xenos", 11, 10, 768),
        ("trooper", "Marines", 8, 14, 256), ("crusher", "Xenos", 11, 14, 768),
        ("ranger", "Marines", 8, 18, 256), ("crusher", "Xenos", 11, 18, 768),
        ("assault", "Marines", 8, 22, 256), ("crusher", "Xenos", 11, 22, 768),
        ("resin-silo", "Xenos", 20, 28, 0),
    ]},
    # A crusher charges a marine, who is thrown away (see scenarios/test-knockback.lua).
    "scenario-knockback": {"scripts": ("test-knockback",), "size": (48, 24), "drop_conquest": True, "extra_rules": "rifleman:\n\tHealth:\n\t\tHP: 3000\ncrusher:\n\tArmament@PRIMARY:\n\t\tWeapon: TGMCCharge\n", "actors": [
        ("crusher", "Xenos", 10, 10, 0), ("rifleman", "Marines", 16, 10, 512), ("resin-silo", "Xenos", 40, 20, 0),
    ]},
    # The caste abilities (see scenarios/test-abilities.lua): a ravager, a praetorian facing a marine, a warrior beside one, a carrier.
    "scenario-abilities": {"scripts": ("test-abilities",), "size": (48, 32), "drop_conquest": True, "extra_rules": "rifleman:\n\tHealth:\n\t\tHP: 3000\n", "actors": [
        ("ravager", "Xenos", 6, 4, 0),
        ("praetorian", "Xenos", 10, 10, 256), ("rifleman", "Marines", 12, 10, 0),
        ("warrior", "Xenos", 10, 16, 256), ("rifleman", "Marines", 11, 16, 0),
        ("carrier", "Xenos", 30, 24, 768), ("rifleman", "Marines", 44, 28, 0),
        ("resin-silo", "Xenos", 40, 4, 0),
    ]},
    # Not a test: marines being clawed, to see the blood on the floor (see Bleeds in tgmc/code/Blood.cs).
    "shot-bleed": {"scripts": ("shot-bleed",), "size": (32, 24), "drop_conquest": True, "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 150\nrifleman:\n\tHealth:\n\t\tHP: 3000\n", "actors": [
        ("rifleman", "Marines", 16, 12, 0), ("rifleman", "Marines", 17, 14, 0),
        ("crusher", "Xenos", 12, 12, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    "shot-shells": {"scripts": ("shot-shells",), "size": (48, 32), "drop_conquest": True, "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 320\n", "actors": [
        ("mortar-emplacement", "Marines", 6, 12, 0), ("artillery-emplacement", "Marines", 6, 18, 0),
        ("rifleman", "Marines", 20, 12, 0), ("rifleman", "Marines", 20, 18, 0),
        ("crusher", "Xenos", 24, 12, 0), ("crusher", "Xenos", 24, 18, 0), ("resin-silo", "Xenos", 40, 28, 0),
    ]},
    "shot-facing": {"scripts": ("shot-facing",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 45\n", "actors": [
        ("rifleman", "Marines", 8, 8, 512),
        ("hunter", "Xenos", 8, 16, 0),
        ("rifleman", "Marines", 10, 8, 512),
        ("hunter", "Xenos", 10, 16, 0),
        ("rifleman", "Marines", 12, 8, 512),
        ("hunter", "Xenos", 12, 16, 0),
        ("rifleman", "Marines", 14, 8, 512),
        ("hunter", "Xenos", 14, 16, 0),
        ("rifleman", "Marines", 16, 8, 512),
        ("hunter", "Xenos", 16, 16, 0),
        ("rifleman", "Marines", 18, 8, 512),
        ("hunter", "Xenos", 18, 16, 0),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    "shot-weeds": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 900\n", "actors": [
        ("weed-node", "Xenos", 10, 10, 0),
        ("weed-node", "Xenos", 14, 10, 0),
        ("medbay", "Marines", 10, 15, 0),
        ("rifleman", "Marines", 20, 20, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "shot-mechs": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 60\n", "actors": [
        ("mech", "Marines", 8, 9, 512),
        ("mech", "Marines", 11, 9, 512),
        ("mech", "Marines", 14, 9, 512),
        ("mech", "Marines", 17, 9, 512),
        ("mech", "Marines", 8, 12, 512),
        ("mech", "Marines", 11, 12, 512),
        ("mech", "Marines", 14, 12, 512),
        ("mech", "Marines", 17, 12, 512),
        ("rifleman", "Marines", 12, 6, 512),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    "shot-labels": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 70\n\t\tSelect: rifleman\n", "actors": [
        ("rifleman", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 13, 12, 512),
        ("facehugger", "Xenos", 11, 10, 0),
        ("crusher", "Xenos", 14, 13, 0),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    "shot-help": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 70\n\t\tClick: HELP_BUTTON\n", "actors": [
        ("medbay", "Marines", 7, 8, 0),
        ("rifleman", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 13, 12, 512),
        ("facehugger", "Xenos", 11, 10, 0),
        ("crusher", "Xenos", 14, 13, 0),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    "shot-group": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 70\n\t\tSelect: rifleman, medic, smartgunner\n", "actors": [
        ("rifleman", "Marines", 10, 10, 768), ("rifleman", "Marines", 10, 11, 768), ("rifleman", "Marines", 10, 12, 768),
        ("smartgunner", "Marines", 9, 11, 768), ("medic", "Marines", 8, 11, 768), ("rifleman", "Marines", 10, 9, 768),
        ("hunter", "Xenos", 15, 10, 256), ("hunter", "Xenos", 15, 12, 256), ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    "shot-rain": {"scripts": ("shot",), "extra_rules": "World:\n\tTgmcOptions:\n\t\tWeatherDefault: rain\n\tScreenshotAt:\n\t\tTick: 250\n", "actors": [
        ("rifleman", "Marines", 10, 10, 512), ("rifleman", "Marines", 12, 11, 512), ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    "shot-stats": {"scripts": ("shot-stats",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 5000\n\t\tAfterGameOver: 30\n", "actors": [
        ("rifleman", "Marines", 10, 10, 512),
        ("runner", "Xenos", 14, 10, 0),
        ("mini-silo", "Xenos", 16, 14, 0),
    ]},
    "shot-xenohud": {"scripts": ("test-evolve",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 110\n\t\tSelect: larva, runner\n", "actors": [
        ("larva", "Xenos", 10, 10, 512),
        ("runner", "Xenos", 12, 10, 512),
        ("rifleman", "Marines", 20, 20, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "shot-codex": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 40\n\t\tClick: CODEX_BUTTON\n", "actors": [
        ("rifleman", "Marines", 10, 10, 512),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "shot-medic": {"scripts": ("shot-medic",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 160\n\t\tClickTick: 20\n\t\tSelect: rifleman\n\t\tClick: CMD_MEDIC\n", "actors": [
        ("medbay", "Marines", 6, 8, 0),
        ("rifleman", "Marines", 15, 12, 512),
        ("rifleman", "Marines", 16, 13, 512),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    "scenario-heavy": {"scripts": ("test-heavy",), "actors": [
        ("heavygunner", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 10, 16, 512),
        ("crusher", "Xenos", 15, 10, 0),
        ("crusher", "Xenos", 15, 16, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-pounce": {"scripts": ("test-pounce",), "actors": [
        ("rifleman", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 20, 20, 0),
        ("runner", "Xenos", 15, 10, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-infest-cure": {"scripts": ("test-infest-cure",), "extra_rules": "^Infantry:\n\tInfestable:\n\t\tBurstDelay: 300\n\t\tHugDuration: 60\n", "actors": [
        ("medic", "Marines", 8, 10, 512),
        ("rifleman", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 20, 20, 0),
        ("facehugger", "Xenos", 12, 10, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-autocure": {"scripts": ("test-autocure",), "extra_rules": "^Infantry:\n\tInfestable:\n\t\tBurstDelay: 300\n\t\tHugDuration: 60\n", "actors": [
        ("medic", "Marines", 8, 10, 512),
        ("rifleman", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 20, 20, 0),
        ("facehugger", "Xenos", 12, 10, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-evolve": {"scripts": ("test-evolve",), "actors": [
        ("larva", "Xenos", 10, 10, 512),
        ("rifleman", "Marines", 20, 20, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-weeds": {"scripts": ("test-weeds",), "actors": [
        ("weed-node", "Xenos", 10, 10, 0),
        ("rifleman", "Marines", 20, 20, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-multiqueue": {"scripts": ("test-multiqueue",), "actors": [
        ("cryo-pod", "Marines", 6, 6, 0),
        ("cryo-pod", "Marines", 12, 6, 0),
        ("rifleman", "Marines", 20, 3, 0),
        ("resin-silo", "Xenos", 16, 16, 0),
    ]},
    "scenario-facing": {"scripts": ("test-facing",), "size": (48, 32), "actors": [
        ("rifleman", "Marines", 10, 10, 0), ("hunter", "Xenos", 10, 5, 0),
        ("rifleman", "Marines", 20, 10, 0), ("hunter", "Xenos", 25, 10, 0),
        ("rifleman", "Marines", 10, 20, 0), ("hunter", "Xenos", 10, 25, 0),
        ("rifleman", "Marines", 30, 20, 0), ("hunter", "Xenos", 25, 20, 0),
        ("resin-silo", "Xenos", 40, 28, 0),
    ]},
    "scenario-rally": {"scripts": ("test-rally",), "actors": [
        ("cryo-pod", "Marines", 6, 6, 0),
        ("rifleman", "Marines", 20, 3, 0),
        ("resin-silo", "Xenos", 16, 16, 0),
    ]},
    # A full match, AI against AI, on the Landing Zone layout. Both sides are scripted players with the Skirmish AI.
    "balance-aivai": {"scripts": ("test-aivai",), "xeno_bot": "skirmish", "marine_bot": "skirmish", "fast": True,
                       "size": (40, 28), "spawns": [(6, 14), (33, 13)], "ground": "landing_zone", "actors": LANDING_ZONE},
    # Hold the Line with a marine bot that stays home (its squad module is removed), to see if six waves are survivable.
    "balance-holdline": {"scripts": ("wave-survival", "test-holdline"), "marine_bot": "skirmish", "fast": True,
                         "drop_conquest": True, "size": (40, 28), "spawns": [(6, 14), (33, 13)], "ground": "landing_zone",
                         "actors": HOLD_THE_LINE, "extra_rules": "Player:\n\t-SquadManagerBotModule@marines-easy:\n\t-SquadManagerBotModule@marines-normal:\n\t-SquadManagerBotModule@marines-hard:\n"},
    # One of each effect-carrying weapon, each pair facing off a few cells apart (see scenarios/test-fx.lua)
    "scenario-fx": {"scripts": ("test-fx",), "actors": [
        ("rifleman", "Marines", 8, 8, 256),
        ("hunter", "Xenos", 12, 8, 768),
        ("smartgunner", "Marines", 8, 11, 256),
        ("sentinel", "Xenos", 13, 11, 768),
        ("grenadier", "Marines", 8, 14, 256),
        ("resin-turret", "Xenos", 15, 14, 768),
        ("sentry-turret", "Marines", 8, 17, 256),
        ("warrior", "Xenos", 12, 17, 768),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    # Every unit type dies once, some by explosion (see scenarios/test-gib.lua). Conquest is dropped: the marines all die.
    "scenario-acid": {"scripts": ("test-acid",), "drop_conquest": True, "actors": [
        ("rifleman", "Marines", 10, 10, 512), ("runner", "Xenos", 11, 10, 0), ("resin-silo", "Xenos", 20, 20, 0),
    ]},
    "scenario-screech": {"scripts": ("test-screech",), "drop_conquest": True, "actors": [
        ("queen", "Xenos", 12, 8, 0), ("rifleman", "Marines", 14, 8, 512), ("rifleman", "Marines", 22, 8, 512),
        ("resin-silo", "Xenos", 20, 20, 0),
    ]},
    "scenario-flame": {"scripts": ("test-flame",), "drop_conquest": True, "actors": [
        ("flamer", "Marines", 10, 10, 256), ("crusher", "Xenos", 13, 10, 0), ("resin-silo", "Xenos", 21, 21, 0),
    ]},
    "scenario-movefire": {"scripts": ("test-movefire",), "size": (48, 32), "drop_conquest": True, "actors": [
        ("rifleman", "Marines", 5, 10, 256), ("sniper", "Marines", 5, 20, 256),
        ("crusher", "Xenos", 14, 8, 0), ("crusher", "Xenos", 14, 18, 0), ("resin-silo", "Xenos", 44, 28, 0),
    ]},
    "scenario-wither": {"scripts": ("test-wither",), "drop_conquest": True, "actors": [
        ("weed-node", "Xenos", 10, 10, 0), ("rifleman", "Marines", 22, 22, 0), ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-emplacement": {"scripts": ("test-emplacement",), "size": (80, 24), "drop_conquest": True, "actors": [
        ("mortar-emplacement", "Marines", 6, 6, 0), ("artillery-emplacement", "Marines", 6, 14, 0),
        ("rifleman", "Marines", 24, 6, 0), ("rifleman", "Marines", 38, 14, 0),
        ("crusher", "Xenos", 27, 6, 0), ("crusher", "Xenos", 41, 14, 0),
    ]},
    # The marine AI calls in CAS by itself on a cluster of hunters it can see (see scenarios/test-ai-cas.lua). Nothing else may kill them: the squads
    # are removed and every unit holds fire.
    "scenario-ai-cas": {"scripts": ("test-ai-cas",), "marine_bot": "skirmish", "drop_conquest": True, "size": (48, 32),
                        "extra_rules": "Player:\n\t-SquadManagerBotModule@marines-easy:\n\t-SquadManagerBotModule@marines-normal:\n\t-SquadManagerBotModule@marines-hard:\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\nordnance-depot:\n\tCondorStrikePower@cas:\n\t\tChargeInterval: 60\n", "actors": [
        ("ordnance-depot", "Marines", 6, 6, 0), ("rifleman", "Marines", 17, 22, 512),
        ("hunter", "Xenos", 22, 22, 0), ("hunter", "Xenos", 23, 23, 0), ("hunter", "Xenos", 22, 24, 0),
        ("hunter", "Xenos", 24, 22, 0), ("hunter", "Xenos", 23, 21, 0), ("hunter", "Xenos", 24, 24, 0),
    ]},
    # The smart modules of the AI, one scenario each (see scenarios/test-ai-*.lua). Squads are removed and units hold fire, so only the module
    # under test acts.
    "scenario-ai-evolve": {"scripts": ("test-ai-evolve",), "xeno_bot": "skirmish", "drop_conquest": True, "size": (48, 32),
                           "extra_rules": "Player:\n\t-SquadManagerBotModule@xenos-easy:\n\t-SquadManagerBotModule@xenos-normal:\n\t-SquadManagerBotModule@xenos-hard:\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": [
        ("resin-silo", "Xenos", 30, 20, 0), ("evolution-tower", "Xenos", 34, 20, 0),
        ("runner", "Xenos", 28, 23, 0), ("runner", "Xenos", 29, 24, 0), ("runner", "Xenos", 30, 25, 0),
        ("rifleman", "Marines", 4, 4, 512),
    ]},
    "scenario-ai-counter": {"scripts": ("test-ai-counter",), "marine_bot": "skirmish", "drop_conquest": True, "size": (48, 32),
                            "extra_rules": "Player:\n\t-SquadManagerBotModule@marines-easy:\n\t-SquadManagerBotModule@marines-normal:\n\t-SquadManagerBotModule@marines-hard:\n\t-UnitBuilderBotModule@skirmish:\n\tUnitBuilderBotModule@only:\n\t\tRequiresCondition: enable-skirmish-ai\n\t\tUnitQueues: Infantry\n\t\tProductionMinCashRequirement: 60\n\t\tUnitsToBuild:\n\t\t\trifleman: 100\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": [
        ("cryo-pod", "Marines", 6, 6, 0), ("armory", "Marines", 10, 6, 0), ("ordnance-depot", "Marines", 14, 6, 0), ("rifleman", "Marines", 17, 22, 512),
        ("hunter", "Xenos", 22, 22, 0), ("hunter", "Xenos", 23, 23, 0), ("hunter", "Xenos", 22, 24, 0),
        ("hunter", "Xenos", 24, 22, 0), ("hunter", "Xenos", 23, 21, 0), ("hunter", "Xenos", 24, 24, 0),
    ]},
    "scenario-ai-medic": {"scripts": ("test-ai-medic",), "marine_bot": "skirmish", "drop_conquest": True, "size": (48, 32),
                          "extra_rules": "Player:\n\t-SquadManagerBotModule@marines-easy:\n\t-SquadManagerBotModule@marines-normal:\n\t-SquadManagerBotModule@marines-hard:\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": [
        ("cryo-pod", "Marines", 6, 6, 0), ("medic", "Marines", 8, 10, 0), ("rifleman", "Marines", 28, 12, 0),
        ("resin-silo", "Xenos", 44, 28, 0),
    ]},
    "scenario-ai-retreat": {"scripts": ("test-ai-retreat",), "marine_bot": "skirmish", "drop_conquest": True, "size": (48, 32),
                            "extra_rules": "Player:\n\t-SquadManagerBotModule@marines-easy:\n\t-SquadManagerBotModule@marines-normal:\n\t-SquadManagerBotModule@marines-hard:\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": [
        ("cryo-pod", "Marines", 6, 6, 0), ("medbay", "Marines", 10, 6, 0), ("rifleman", "Marines", 30, 12, 0),
        ("resin-silo", "Xenos", 44, 28, 0),
    ]},
    "scenario-ai-scout": {"scripts": ("test-ai-scout",), "marine_bot": "hard", "drop_conquest": True, "size": (64, 48),
                          "extra_rules": "Player:\n\t-SquadManagerBotModule@marines-easy:\n\t-SquadManagerBotModule@marines-normal:\n\t-SquadManagerBotModule@marines-hard:\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": [
        ("cryo-pod", "Marines", 6, 6, 0), ("rifleman", "Marines", 8, 8, 0), ("resin-silo", "Xenos", 58, 42, 0),
    ]},
    "scenario-ai-easy": {"scripts": ("test-ai",), "xeno_bot": "easy", "actors": [
        ("rifleman", "Marines", 3, 3, 512),
        ("resin-silo", "Xenos", 16, 16, 0),
    ]},
    # Hive tunnels and hive powers (see scenarios/test-tunnel.lua, test-hive-powers.lua).
    "scenario-tunnel": {"scripts": ("test-tunnel",), "size": (64, 24), "drop_conquest": True, "actors": [
        ("tunnel", "Xenos", 6, 6, 0), ("tunnel", "Xenos", 50, 16, 0), ("tunnel", "Xenos", 20, 6, 0),
        ("runner", "Xenos", 9, 9, 0), ("rifleman", "Marines", 3, 20, 0),
    ]},
    "scenario-hive-powers": {"scripts": ("test-hive-powers",), "xeno_bot": "skirmish", "size": (48, 32), "drop_conquest": True,
                             "extra_rules": "Player:\n\t-SquadManagerBotModule@xenos-easy:\n\t-SquadManagerBotModule@xenos-normal:\n\t-SquadManagerBotModule@xenos-hard:\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\nevolution-tower:\n\tGrantExternalConditionPower@cure:\n\t\tChargeInterval: 60\n\tCallOfTheBurrowedPower@burrowed:\n\t\tChargeInterval: 60\n", "actors": [
        ("evolution-tower", "Xenos", 6, 6, 0), ("maturity-tower", "Xenos", 10, 6, 0),
        ("hunter", "Xenos", 24, 20, 0), ("hunter", "Xenos", 25, 21, 0), ("hunter", "Xenos", 24, 22, 0), ("hunter", "Xenos", 26, 20, 0), ("hunter", "Xenos", 26, 22, 0),
        ("rifleman", "Marines", 30, 22, 512), ("rifleman", "Marines", 31, 24, 512),
        ("resin-silo", "Xenos", 3, 3, 0),
    ]},
    "scenario-boiler": {"scripts": ("test-boiler",), "size": (48, 24), "drop_conquest": True, "extra_rules": "^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": [
        ("boiler", "Xenos", 6, 10, 0), ("rifleman", "Marines", 17, 10, 0),
    ]},
    "scenario-gas": {"scripts": ("test-gas",), "size": (48, 24), "drop_conquest": True, "extra_rules": "^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": [
        ("defiler", "Xenos", 6, 10, 0), ("rifleman", "Marines", 14, 10, 0),
    ]},
    "scenario-hive": {"scripts": ("test-hive",), "drop_conquest": True, "actors": [
        ("forward-hive", "Xenos", 10, 10, 0), ("resin-trap", "Xenos", 18, 18, 0), ("rifleman", "Marines", 19, 18, 512),
    ]},
    "scenario-gib": {"scripts": ("test-gib",), "drop_conquest": True, "actors": [
        ("rifleman", "Marines", 6, 6, 512), ("medic", "Marines", 6, 8, 512), ("engineer", "Marines", 6, 10, 512),
        ("smartgunner", "Marines", 6, 12, 512), ("grenadier", "Marines", 6, 14, 512),
        ("runner", "Xenos", 12, 6, 0), ("hunter", "Xenos", 12, 8, 0), ("sentinel", "Xenos", 12, 10, 0),
        ("drone", "Xenos", 12, 12, 0), ("warrior", "Xenos", 12, 14, 0), ("queen", "Xenos", 12, 16, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-sounds": {"scripts": ("test-sounds", "sound-list"), "generated": ("sound-list",), "actors": [
        ("rifleman", "Marines", 10, 10, 0),
        ("resin-silo", "Xenos", 16, 16, 0),
    ]},
    "scenario-victory": _scenario("test-victory", [
        ("rifleman", "Marines", 10, 10, 512),
        ("runner", "Xenos", 14, 10, 0),
        ("mini-silo", "Xenos", 16, 14, 0),
    ]),
}


def write_sound_list(path):
    """A Lua file listing every converted sound, every Speech notification and every music track, for test-sounds.lua."""
    here = os.path.dirname(os.path.abspath(__file__))
    notifications = open(os.path.join(here, "..", "tgmc", "audio", "notifications.yaml"), encoding="utf-8").read()
    speech = notifications.split("Speech:")[1]
    names = re.findall(r"^\t\t([A-Za-z]+):", speech, re.M)
    music = open(os.path.join(here, "..", "tgmc", "audio", "music.yaml"), encoding="utf-8").read()
    tracks = re.findall(r"^([a-z0-9-]+):", music, re.M)
    quote = lambda items: ", ".join(f'"{i}"' for i in items)  # noqa: E731
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Generated by make_placeholders.py. Do not edit.\n")
        f.write(f"SoundFiles = {{ {quote(f'{n}.ogg' for n in sorted(build_sounds.SOUNDS))} }}\n")
        f.write(f"SpeechNotifications = {{ {quote(names)} }}\n")
        f.write(f"MusicTracks = {{ {quote(tracks)} }}\n")


def write_map(folder, title, size_w, size_h, placed, visibility, spawns, scripts=(), ground=flat_ground,
              category="Skirmish", drop_conquest=False, xeno_bot=None, marine_bot=None, fast=False, extra_rules="",
              music=False):
    # A scenario map has no slot for the xenos: they are a scripted player, so Lua can find them and they never act.
    os.makedirs(folder, exist_ok=True)
    cells = size_w * size_h
    # map.bin: version byte, width, height, u32 tiles offset, u32 heights offset (0), u32 resources offset (0),
    # then per cell (x-major): u16 template id, u8 variant index.
    header = struct.pack("<BHHIII", 2, size_w, size_h, 17, 0, 0)
    body = b"".join(struct.pack("<HB", *ground(x, y)) for x in range(size_w) for y in range(size_h))
    with open(os.path.join(folder, "map.bin"), "wb") as f:
        f.write(header + body)

    actors = []
    # Spawn points come first so that Spawn: 1 and 2 on the players below are their indices.
    placed = [("mpspawn", "Neutral", x, y, 0) for x, y in spawns] + list(placed)
    for i, (name, owner, x, y, facing) in enumerate(placed):
        actors.append(f"\tActor{i}: {name}\n\t\tOwner: {owner}\n\t\tLocation: {x},{y}\n\t\tFacing: {facing}\n")

    script = bool(scripts)
    rules_line = ""
    if scripts:
        rules_line = "Rules: rules.yaml\n\n"
        listed = [f"{name}.lua" for name in scripts]
        if music:
            # A map's Scripts replaces the world's, which holds the music script. It goes last: it wraps the map's WorldLoaded.
            listed.append("tgmc|scripts/music.lua")
        rules = "World:\n\tLuaScript:\n\t\tScripts: " + ", ".join(listed) + "\n"
        if fast:
            # Scenario maps run at the fastest game speed so a long match (such as AI against AI) finishes quickly.
            rules += "World:\n\tMapOptions:\n\t\tGameSpeed: fastest\n"
        rules += extra_rules
        if drop_conquest:
            # The script owns the objective, and the xenos start with nothing, so conquest would end the game at once.
            rules += "Player:\n\t-ConquestVictoryConditions:\n"
        with open(os.path.join(folder, "rules.yaml"), "w", encoding="utf-8", newline="\n") as f:
            f.write(rules)
        for name in scripts:
            if name == "sound-list":
                write_sound_list(os.path.join(folder, "sound-list.lua"))
                continue
            shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenarios", f"{name}.lua"),
                            os.path.join(folder, f"{name}.lua"))

    xeno_bot_line = f"\t\tBot: {xeno_bot}\n" if xeno_bot else ""
    marine_bot_line = f"\t\tBot: {marine_bot}\n" if marine_bot else ""
    # A map needs one playable slot even when both sides are bots. This one has no units and never wins or loses.
    observer_block = ("\tPlayerReference@Observer:\n\t\tName: Observer\n\t\tPlayable: True\n\t\tNonCombatant: True\n"
                      "\t\tFaction: marines\n\t\tLockFaction: True\n") if marine_bot else ""
    yaml = f"""MapFormat: 12

RequiresMod: tgmc

Title: {title}

Author: TGMC OpenRA mod

Tileset: TGMC

MapSize: {size_w},{size_h}

Bounds: 1,1,{size_w - 2},{size_h - 2}

Visibility: {visibility}

{rules_line}Categories: {category}

Players:
	PlayerReference@Neutral:
		Name: Neutral
		OwnsWorld: True
		NonCombatant: True
	PlayerReference@Marines:
		Name: Marines
		Playable: {not marine_bot}
{marine_bot_line}		Faction: marines
		LockFaction: True
		Enemies: Xenos
		Spawn: 1
		LockSpawn: True
	PlayerReference@Xenos:
		Name: Xenos
		Playable: {not script}
{xeno_bot_line}		Faction: xenos
		LockFaction: True
		Enemies: Marines
		Spawn: 2
		LockSpawn: True
{observer_block}
Actors:
{"".join(actors)}"""
    with open(os.path.join(folder, "map.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(yaml)

    colours = {ROCK: (0x3A, 0x3A, 0x3A, 255), GRASS: (0x2E, 0x52, 0x30, 255), WATER: (0x1C, 0x3A, 0x5E, 255), FORD: (0x4A, 0x72, 0x86, 255), DIRT: (0x7A, 0x62, 0x40, 255)}
    preview = Image.new("RGBA", (size_w, size_h))
    preview.putdata([colours[ground(x, y)[0]] for y in range(size_h) for x in range(size_w)])
    preview.save(os.path.join(folder, "map.png"))


def write_tgmc_map(folder, title, rows, marines, xenos):
    """A skirmish map from a converted TGMC map. Landing Zone's two bases go at the given centres, on open ground."""
    h, w = len(rows), len(rows[0])
    land = [list(r) for r in rows]
    centres = {"Marines": (marines, (6, 14)), "Xenos": (xenos, (33, 13))}

    def place(actors, owner):
        # Slide the base around the chosen centre to where most of its cells already are land. A base is its actors and its spawn point.
        (cx, cy), (bx, by) = centres[owner]
        pts = [(x, y) for _, o, x, y, _ in actors if o == owner] + [(bx, by)]
        fits = lambda dx, dy: sum(land[y + dy][x + dx] in "GDF" for x, y in pts)  # noqa: E731
        shifts = [(i, j) for i in range(-6, 7) for j in range(-6, 7)
                  if all(2 <= x + cx - bx + i <= w - 3 and 2 <= y + cy - by + j <= h - 3 for x, y in pts)]
        i, j = max(shifts, key=lambda s: (fits(cx - bx + s[0], cy - by + s[1]), -abs(s[0]) - abs(s[1])))
        dx, dy = cx - bx + i, cy - by + j
        for x, y in pts:  # clear what is left: each cell and the ring around it
            for ax in range(x + dx - 1, x + dx + 2):
                for ay in range(y + dy - 1, y + dy + 2):
                    if 1 <= ax < w - 1 and 1 <= ay < h - 1 and land[ay][ax] in "RW":
                        land[ay][ax] = "D"
        return [(n, o, x + dx, y + dy, f) for n, o, x, y, f in actors if o == owner], (bx + dx, by + dy)

    actors, spawn_m = place(LANDING_ZONE, "Marines")
    xeno_actors, spawn_x = place(LANDING_ZONE, "Xenos")
    # The bases must be joined by walkable ground, or the match can never be won. Where TGMC's own walls cut them apart (the
    # full size maps keep every wall), dig the cheapest tunnel through the rock: open ground costs 1, rock 6.
    import heapq
    walk = "GDF"
    dist, prev, heap = {spawn_m: 0}, {}, [(0, spawn_m)]
    while heap:
        d, (x, y) = heapq.heappop(heap)
        if (x, y) == spawn_x:
            break
        if d > dist[(x, y)]:
            continue
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 1 <= n[0] < w - 1 and 1 <= n[1] < h - 1 and land[n[1]][n[0]] != "W":
                nd = d + (1 if land[n[1]][n[0]] in walk else 6)
                if nd < dist.get(n, 1 << 30):
                    dist[n], prev[n] = nd, (x, y)
                    heapq.heappush(heap, (nd, n))
    assert spawn_x in dist, f"{title}: the xeno base at {spawn_x} cannot be reached from the marine base at {spawn_m}"
    cell = spawn_x
    while cell != spawn_m:
        if land[cell[1]][cell[0]] == "R":
            land[cell[1]][cell[0]] = "D"
        cell = prev[cell]
    codes = {"G": GRASS, "D": DIRT, "F": FORD, "W": WATER, "R": ROCK}
    write_map(folder, title, w, h, actors + xeno_actors, "Lobby", [spawn_m, spawn_x],
              ground=lambda x, y: (codes[land[y][x]], 0), category="Conquest")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tgmc", help="a TGMC checkout; with it the maps converted from TGMC's own (tgmc_dmm.MAPS) are written too")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    write_palette(os.path.join(args.out, "tgmc.pal"))
    write_cursor(os.path.join(args.out, "cursor.png"))
    write_clock(os.path.join(args.out, "clock.png"))
    write_shroud_tiles(args.out, tile=32)
    write_rally_marker(args.out)
    write_move_flash(args.out)
    write_cas_icon(args.out)
    write_hive_icon(args.out)
    write_lights(args.out)
    write_overlay(args.out)
    write_acid_pool(args.out)
    write_repair_fx(args.out)
    write_map(os.path.join(args.out, "maps", "test-field"), "TGMC test field", 24, 24, TEST_FIELD, "Lobby, Shellmap", [(10, 12), (14, 12)])
    write_map(os.path.join(args.out, "maps", "landing-zone"), "Landing Zone", 40, 28, LANDING_ZONE, "Lobby", [(6, 14), (33, 13)],
              ground=landing_zone_ground, category="Conquest")
    for name, (title, w, h, xeno_dx, dy, ground) in SKIRMISH_MAPS.items():
        actors = _skirmish_actors(xeno_dx, dy)
        for _, _, x, y, _ in actors:
            assert 2 <= x <= w - 3 and 2 <= y <= h - 3 and ground(x, y)[0] != WATER, f"{name}: actor at {x},{y} is off the map or in water"
        write_map(os.path.join(args.out, "maps", name), title, w, h, actors, "Lobby", [(6, 14 + dy), (33 + xeno_dx, 13 + dy)],
                  ground=ground, category="Conquest")
    if args.tgmc:
        for name, spec in tgmc_dmm.MAPS.items():
            write_tgmc_map(os.path.join(args.out, "maps", name), spec["title"], *tgmc_dmm.load(args.tgmc, spec))
    for name, sc in SCENARIOS.items():
        width, height = sc.get("size", (24, 24))
        write_map(os.path.join(args.out, "maps", name), name, width, height, sc["actors"], "MissionSelector",
                  sc.get("spawns", [(10, 8), (19, 17)]), scripts=sc["scripts"],
                  drop_conquest=sc.get("drop_conquest", False), xeno_bot=sc.get("xeno_bot"),
                  marine_bot=sc.get("marine_bot"), fast=sc.get("fast", True),
                  extra_rules=sc.get("extra_rules", ""),
                  ground=landing_zone_ground if sc.get("ground") == "landing_zone" else flat_ground)
    write_map(os.path.join(args.out, "maps", "hold-the-line"), "Hold the Line", 40, 28, HOLD_THE_LINE, "Lobby",
              [(6, 14), (33, 13)], scripts=("wave-survival",), ground=landing_zone_ground, category="Survival",
              drop_conquest=True, music=True)
    print(f"placeholders written to {args.out}")


if __name__ == "__main__":
    main()
