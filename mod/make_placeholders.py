"""Generate the non-TGMC pieces the mod needs to load and show a test field.

Nothing here is TGMC art. It writes:
  tgmc.pal                      a flat grey 256-colour palette (OpenRA needs one for its palette setup)
  cursor.png                    the cursors: arrow, move, blocked, attack, heal, repair, ability, enter
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

from PIL import Image, ImageDraw, ImageFilter, PngImagePlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_sounds  # noqa: E402
import build_maptiles  # noqa: E402
import build_tileset  # noqa: E402
import tgmc_dmi  # noqa: E402
import tgmc_dmm  # noqa: E402

CLOCK_W, CLOCK_H, CLOCK_FRAMES, CLOCK_COLS = 62, 46, 30, 6  # matches the sidebar palette's IconSize
# Template ids in tilesets/ground.yaml. Grass lists two images, which the engine picks between per cell. The byte
# after the id in map.bin is the tile's index within its template: 0, except where write_map picks a grass-edge frame.
GRASS, WATER, FORD, DIRT, ROCK = 1, 2, 3, 4, 5
WALL = 6  # rock that heavy weapons can knock down


def walls_ground(x, y):
    """Grass with a wall of three cells thick at x 14 to 16, y 8 to 15."""
    return (WALL if 14 <= x <= 16 and 8 <= y <= 15 else GRASS), 0

def doorline_ground(x, y):
    """Grass with an uncrossable line of rock at x 14, except a gap at y 11 (the door)."""
    return (WALL if x == 14 and y != 11 else GRASS), 0


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
    ("rifleman", "Marines", 9, 17, 256),
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


def shell_ground(x, y):
    """The menu backdrop: a dirt landing pad where the Alamo sets down, and a track from it toward the hive."""
    if (23 <= x <= 33 and 3 <= y <= 24) or (y in (26, 27) and 33 <= x <= 55):
        return DIRT, 0
    return flat_ground(x, y)


def landing_zone_ground(x, y):
    """A two-cell river down the middle with three fords, and a dirt road linking the two bases."""
    if x in (19, 20):
        return (FORD, 0) if y in (4, 5, 12, 13, 14, 15, 22, 23) else (WATER, 0)
    if y == 13 and (6 <= x <= 32):
        return DIRT, 0
    return flat_ground(x, y)


def evac_ground(x, y):
    """64x48. Evac: a road from the marine base in the west to the landing zone (dirt, x 38 to 50, y 13 to 35) in the east, two rock
    outcrops that funnel the north and south approaches, and a pond in the middle."""
    if 38 <= x <= 50 and 13 <= y <= 35:
        return DIRT, 0
    if (y == 24 and 8 <= x <= 38) or (x == 16 and 14 <= y <= 34):
        return DIRT, 0
    if _ellipse(x, y, 26, 12, 4, 2) or _ellipse(x, y, 26, 36, 4, 2):
        return ROCK, 0
    if _ellipse(x, y, 30, 24, 2, 3) and y != 24:
        return WATER, 0
    return GRASS, 0


def _ellipse(x, y, cx, cy, rx, ry):
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def _road(x, y, row, x0, x1):
    return y == row and x0 <= x <= x1


def canyon_run_ground(x, y):
    """52x28. Canyon walls of rock leave a six-wide lane down the middle and two two-wide trails along the edges: one choke, two flanks."""
    if 15 <= x <= 36:
        if 11 <= y <= 16:
            return (DIRT if y in (13, 14) else GRASS), 0
        return (GRASS, 0) if y in (3, 4, 23, 24) else (ROCK, 0)
    return (DIRT, 0) if _road(x, y, 13, 6, 45) else (GRASS, 0)


def jungle_crossing_ground(x, y):
    """44x28. A lake in the middle: go round it by the north or south shore, or wade the causeway through the centre."""
    if _ellipse(x, y, 22, 13.5, 7, 9):
        return (FORD, 0) if y in (13, 14) else (WATER, 0)
    if any(_ellipse(x, y, cx, cy, 2, 2) for cx, cy in ((12, 22), (32, 22))):  # none in the north: the landing pads are there
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


def twin_rivers_ground(x, y):
    """64x48. Two rivers run north to south between the bases, each with three fords that do not line up: an army crossing both zigzags, and the
    island between them is a killing ground with two rock outcrops."""
    if x in (22, 23):
        return (FORD, 0) if y in (10, 11, 12, 23, 24, 25, 36, 37, 38) else (WATER, 0)
    if x in (40, 41):
        return (FORD, 0) if y in (5, 6, 7, 23, 24, 25, 41, 42, 43) else (WATER, 0)
    if _ellipse(x, y, 32, 12, 3, 2) or _ellipse(x, y, 32, 36, 3, 2):
        return ROCK, 0
    return (DIRT, 0) if y in (23, 24) and 6 <= x <= 58 else (GRASS, 0)


def quarry_pit_ground(x, y):
    """64x48. A rock ring around a dirt pit in the middle, open at the four compass points: whoever holds the pit sees all four roads. Ponds in the
    corners, a dirt road from each base to the pit."""
    import math
    dist = math.hypot(x - 32, y - 24)
    angle = math.degrees(math.atan2(y - 24, x - 32)) % 360
    if 8 <= dist <= 10:
        gap = any(abs(((angle - a + 180) % 360) - 180) <= 14 for a in (0, 90, 180, 270))
        return (DIRT, 0) if gap else (ROCK, 0)
    if dist < 8:
        return DIRT, 0
    if any(_ellipse(x, y, cx, cy, 3, 3) for cx, cy in ((16, 8), (48, 40), (16, 40), (48, 8))):
        return WATER, 0
    return (DIRT, 0) if y in (23, 24) and 6 <= x <= 58 else (GRASS, 0)


def broken_bridge_ground(x, y):
    """64x48. A rift cuts the map from the north-west to the south-east: water, rock lips on both sides, and three bridges. Each base can also flank
    round the ends of the rift, a long way."""
    centre = 20 + y * 0.5
    d = x - centre
    bridges = y in (10, 11, 12, 23, 24, 25, 36, 37, 38)
    if abs(d) <= 2:
        return (FORD, 0) if bridges else (WATER, 0)
    if abs(d) <= 3.5 and not bridges:
        return ROCK, 0
    return (DIRT, 0) if y in (23, 24) and 6 <= x <= 58 else (GRASS, 0)


def crossroads_ground(x, y):
    """96x96, four bases, one toward each corner. Two roads cross in a walled yard in the middle (four gates); each road fords a lake
    on its way in, and a rock outcrop stands between each base and the yard."""
    road_x, road_y = x in (47, 48), y in (47, 48)
    if 40 <= x <= 55 and 40 <= y <= 55:
        return (WALL if (x in (40, 55) or y in (40, 55)) and not (road_x or road_y) else DIRT), 0
    if any(_ellipse(x, y, *lake) for lake in ((47.5, 22, 7, 4), (47.5, 73, 7, 4), (22, 47.5, 4, 7), (73, 47.5, 4, 7))):
        return (FORD if road_x or road_y else WATER), 0
    if any(_ellipse(x, y, cx, cy, 3, 3) for cx, cy in ((30, 30), (65, 30), (30, 65), (65, 65))):
        return ROCK, 0
    return (DIRT if (road_y and 6 <= x <= 89) or (road_x and 6 <= y <= 89) else GRASS), 0


def desert_outpost_ground(x, y):
    """72x56. A walled compound in the middle, on the road between the bases, with a gate in each side; rock mesas north and south of the road."""
    road = y in (28, 29)
    if 30 <= x <= 41 and 22 <= y <= 35:
        return (WALL if (x in (30, 41) or y in (22, 35)) and not road and x not in (35, 36) else DIRT), 0
    if any(_ellipse(x, y, *mesa) for mesa in ((20, 14, 5, 3), (20, 43, 5, 3), (51, 14, 5, 3), (51, 43, 5, 3), (36, 9, 4, 2), (36, 48, 4, 2))):
        return ROCK, 0
    return (DIRT if road and 8 <= x <= 63 else GRASS), 0


def ice_shelf_ground(x, y):
    """72x48. Two ice walls run north to south, each with three passes; frozen lakes (fords: slow, no cover) lie in the open, and two
    cracks of open water flank the middle."""
    if x in (18, 19, 52, 53) and not (10 <= y <= 13 or 23 <= y <= 26 or 34 <= y <= 37):
        return ROCK, 0
    if _ellipse(x, y, 36, 10, 2, 3) or _ellipse(x, y, 36, 38, 2, 3):
        return WATER, 0
    if any(_ellipse(x, y, *lake) for lake in ((24, 12, 6, 4), (47, 36, 6, 4), (36, 24, 5, 3))):
        return FORD, 0
    return (DIRT if y in (24, 25) and 8 <= x <= 63 else GRASS), 0


def lava_fields_ground(x, y):
    """72x56. Two winding rivers of lava between the bases, three bridges over each; rock outcrops north and south of the middle."""
    import math
    bridge = 9 <= y <= 11 or 27 <= y <= 30 or 45 <= y <= 47
    if any(abs(x - centre) <= 1.5 for centre in (24 + 3 * math.sin(y / 6), 47 + 3 * math.sin(y / 6 + 2))):
        return (FORD if bridge else WATER), 0
    if _ellipse(x, y, 36, 14, 4, 3) or _ellipse(x, y, 36, 42, 4, 3):
        return ROCK, 0
    return (DIRT if y in (28, 29) and 8 <= x <= 63 else GRASS), 0


def palette_entries():
    """A plain grey ramp. Only the palette-based paths read it; the TGMC-free tiles and sprites are RGBA."""
    return [(i, i, i) for i in range(256)]


def write_palette(path):
    with open(path, "wb") as f:
        f.write(bytes(c for rgb in palette_entries() for c in rgb))


# The cursor sheet's frames, in order (tgmc/cursors.yaml names them by Start). The arrow's tip is its hot spot; the others point with their centre.
CURSOR_FRAMES = ("default", "move", "blocked", "attack", "attack-far", "heal", "repair", "ability", "enter")


def write_cursor(path):
    """The cursors, drawn here so the mod has them without any TGMC art: one 24 px frame for each name in CURSOR_FRAMES, so the
    player sees what a click will do. default: a white arrow. move: green chevrons. blocked: a barred circle. attack: a red
    crosshair (orange when the target is out of range, purple for an ability). heal: a green cross. repair: a yellow wrench.
    enter: a blue arrow into a bracket. A heal or repair target out of reach keeps its own picture: the unit walks there and does it."""
    size, c = 24, 12
    sheet = Image.new("RGBA", (size * len(CURSOR_FRAMES), size), (0, 0, 0, 0))

    def frame(draw_it):
        # Drawn twice: a black copy one pixel wider underneath, so the cursor reads on any ground.
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw_it(ImageDraw.Draw(im), None, 3)
        draw_it(ImageDraw.Draw(im), True, 1)
        return im

    def cross(colour):
        def f(d, top, w):
            col = colour if top else (0, 0, 0, 255)
            d.ellipse([c - 7, c - 7, c + 7, c + 7], outline=col, width=w)
            for a, b in (((c, 1), (c, 8)), ((c, 15), (c, 22)), ((1, c), (8, c)), ((15, c), (22, c))):
                d.line([a, b], fill=col, width=w)
        return f

    def arrow(d, top, w):
        pts = [(1, 1), (1, 16), (5, 12), (8, 19), (11, 18), (8, 11), (13, 11)]
        d.polygon(pts, fill=(255, 255, 255, 255) if top else (0, 0, 0, 255), outline=(0, 0, 0, 255))

    def move(d, top, w):
        col = (90, 230, 110, 255) if top else (0, 0, 0, 255)
        for dy in (0, 7):
            d.line([(c - 7, 5 + dy), (c, 12 + dy), (c + 7, 5 + dy)], fill=col, width=w + 1)

    def blocked(d, top, w):
        col = (230, 70, 60, 255) if top else (0, 0, 0, 255)
        d.ellipse([c - 8, c - 8, c + 8, c + 8], outline=col, width=w + 1)
        d.line([(c - 5, c + 5), (c + 5, c - 5)], fill=col, width=w + 1)

    def heal(d, top, w):
        col = (90, 230, 110, 255) if top else (0, 0, 0, 255)
        g = 0 if top else 1
        d.rectangle([c - 3 - g, c - 9 - g, c + 3 + g, c + 9 + g], fill=col)
        d.rectangle([c - 9 - g, c - 3 - g, c + 9 + g, c + 3 + g], fill=col)

    def repair(d, top, w):
        col = (250, 205, 60, 255) if top else (0, 0, 0, 255)
        d.line([(6, 18), (15, 9)], fill=col, width=w + 2)
        d.arc([11, 2, 21, 12], start=20, end=250, fill=col, width=w + 2)

    def enter(d, top, w):
        col = (90, 170, 250, 255) if top else (0, 0, 0, 255)
        d.line([(c, 2), (c, 14)], fill=col, width=w + 1)
        d.line([(c - 5, 9), (c, 14), (c + 5, 9)], fill=col, width=w + 1)
        d.line([(4, 15), (4, 21), (20, 21), (20, 15)], fill=col, width=w + 1)

    drawers = {"default": arrow, "move": move, "blocked": blocked, "attack": cross((240, 60, 50, 255)), "attack-far": cross((250, 160, 50, 255)),
               "heal": heal, "repair": repair, "ability": cross((190, 110, 250, 255)), "enter": enter}
    for i, name in enumerate(CURSOR_FRAMES):
        sheet.paste(frame(drawers[name]), (size * i, 0))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{size},{size}")
    meta.add_text("FrameAmount", str(len(CURSOR_FRAMES)))
    sheet.save(path, pnginfo=meta)


def write_shroud_tiles(out, tile=32):
    """Edge tiles for ShroudRenderer. Frame i - 1 darkens the quadrants named by the bits of i (1 TL, 2 TR, 4 BR, 8 BL).

    Each quadrant's darkness is a value at its centre, bilinearly blended across the tile, so the edge fades over
    about half a tile instead of stepping at the quadrant border.
    """
    half = tile // 2
    centres = {1: (half / 2, half / 2), 2: (half + half / 2, half / 2), 4: (half + half / 2, half + half / 2), 8: (half / 2, half + half / 2)}
    # Fog is a blue-grey veil, not half black: explored ground stays readable and loses some of its colour.
    for name, rgb, alpha in (("shroud", (0, 0, 0), 255), ("fog", (20, 24, 34), 105)):
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
                    px[tile * (pattern - 1) + x, y] = rgb + (a,)
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", f"{tile},{tile}")
        meta.add_text("FrameAmount", "14")
        sheet.save(os.path.join(out, f"{name}.png"), pnginfo=meta)

        full = Image.new("RGBA", (tile, tile), rgb + (alpha,))
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


def draw_bell(d, cx, cy, body, clapper):
    """The town bell (Recall power): a bell with its clapper and two ring lines."""
    d.polygon([(cx - 4, cy - 12), (cx + 4, cy - 12), (cx + 10, cy + 6), (cx - 10, cy + 6)], fill=body)
    d.ellipse([cx - 3, cy + 5, cx + 3, cy + 11], fill=clapper)
    d.arc([cx - 18, cy - 14, cx - 8, cy + 4], 120, 240, fill=clapper, width=2)
    d.arc([cx + 8, cy - 14, cx + 18, cy + 4], -60, 60, fill=clapper, width=2)


HIVE_ICONS = ["cure", "burrowed", "rage", "bell"]


def write_hive_icon(out):
    """The palette icons for the hive powers (62x46 each, in HIVE_ICONS order): a small drawing and a short name; the HUD tile is the card. No TGMC art."""
    w, h = 62, 46
    img = Image.new("RGBA", (w * len(HIVE_ICONS), h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    green, red, amber, white = (110, 230, 90, 255), (240, 70, 60, 255), (255, 170, 40, 255), (240, 240, 230, 255)
    labels = ["CURE", "BURROW", "RAGE", "RECALL"]
    for i, name in enumerate(HIVE_ICONS):
        ox = w * i
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
        elif name == "bell":
            draw_bell(d, cx, cy, amber, white)
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


def write_shockwave(out):
    """A ring that grows and fades, 256x256, ten frames: the shockwave of a big blast, drawn over the ground with additive blending. No TGMC art."""
    size, frames = 256, 10
    img = Image.new("RGBA", (size * frames, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for f in range(frames):
        radius = 20 + (size / 2 - 24) * f / (frames - 1)
        alpha = int(190 * (1 - f / frames) ** 1.4)
        width = 3 + int(5 * (1 - f / frames))
        cx = size * f + size // 2
        d.ellipse([cx - radius, size // 2 - radius, cx + radius, size // 2 + radius], outline=(255, 215, 150, alpha), width=width)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{size},{size}")
    meta.add_text("FrameAmount", str(frames))
    img.save(os.path.join(out, "shockwave.png"), pnginfo=meta)


def write_pod_icon(out):
    """The palette icon of the drop pod power (62x46): a pod falling in flames. No TGMC art."""
    w, h = 62, 46
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = 31
    d.polygon([(cx, 6), (cx - 8, 24), (cx + 8, 24)], fill=(120, 150, 255, 255))
    d.rectangle([cx - 6, 20, cx + 6, 28], fill=(200, 210, 230, 255))
    d.polygon([(cx - 5, 28), (cx + 5, 28), (cx, 36)], fill=(255, 150, 40, 255))
    d.text((cx - 3 * 3, 35), "POD", fill=(240, 240, 230, 255))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{w},{h}")
    meta.add_text("FrameAmount", "1")
    img.save(os.path.join(out, "pod-icon.png"), pnginfo=meta)


SUPPORT_ICONS = ["supply", "sensor", "smoke", "orbital", "sentry", "mortar", "mech", "bell"]


def write_support_icons(out):
    """The palette icons of the marine support powers (62x46 each, in SUPPORT_ICONS order): a small drawing and a short name; the HUD tile is the card. No TGMC art."""
    import math
    w, h = 62, 46
    img = Image.new("RGBA", (w * len(SUPPORT_ICONS), h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white, blue, amber, red, grey = (240, 240, 230, 255), (110, 150, 255, 255), (255, 170, 40, 255), (240, 80, 60, 255), (170, 176, 186, 255)
    labels = ["SUPPLY", "SENSOR", "SMOKE", "ORBIT", "SENTRY", "MORTAR", "MECH", "RECALL"]
    for i, name in enumerate(SUPPORT_ICONS):
        ox = w * i
        cx, cy = ox + 31, 19
        if name == "supply":
            d.rectangle([cx - 10, cy - 7, cx + 10, cy + 8], fill=(150, 120, 70, 255), outline=white)
            d.rectangle([cx - 2, cy - 4, cx + 2, cy + 5], fill=white)
            d.rectangle([cx - 6, cy - 1, cx + 6, cy + 1], fill=white)
        elif name == "sensor":
            for r in (5, 10, 15):
                d.arc([cx - r, cy - r, cx + r, cy + r], 200, 340, fill=blue, width=2)
            d.ellipse([cx - 2, cy + 3, cx + 2, cy + 7], fill=white)
        elif name == "smoke":
            for dx, dy, r in ((-8, 3, 7), (0, -2, 9), (8, 3, 7)):
                d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=grey)
        elif name == "orbital":
            d.line([cx, cy - 14, cx, cy + 6], fill=red, width=3)
            d.ellipse([cx - 10, cy + 2, cx + 10, cy + 14], outline=amber, width=2)
            d.ellipse([cx - 4, cy + 6, cx + 4, cy + 12], fill=white)
        elif name == "sentry":
            d.rectangle([cx - 8, cy + 2, cx + 8, cy + 9], fill=grey)
            d.rectangle([cx - 3, cy - 5, cx + 3, cy + 2], fill=blue)
            d.rectangle([cx, cy - 6, cx + 14, cy - 3], fill=white)
        elif name == "mortar":
            d.polygon([(cx - 9, cy + 9), (cx + 9, cy + 9), (cx + 3, cy - 2), (cx - 3, cy - 2)], fill=grey)
            d.line([cx, cy - 2, cx + 8, cy - 14], fill=white, width=4)
            d.ellipse([cx + 8, cy - 18, cx + 14, cy - 12], fill=amber)
        elif name == "mech":
            d.rectangle([cx - 6, cy - 4, cx + 6, cy + 6], fill=grey)
            d.rectangle([cx - 4, cy - 9, cx + 4, cy - 4], fill=grey)
            d.rectangle([cx - 11, cy - 3, cx - 7, cy + 5], fill=white)
            d.rectangle([cx + 7, cy - 3, cx + 11, cy + 5], fill=white)
            d.rectangle([cx - 4, cy + 6, cx - 1, cy + 11], fill=grey)
            d.rectangle([cx + 1, cy + 6, cx + 4, cy + 11], fill=grey)
            d.rectangle([cx + 6, cy - 12, cx + 12, cy - 9], fill=red)
        elif name == "bell":
            draw_bell(d, cx, cy, amber, white)
        d.text((ox + 31 - 3 * len(labels[i]), 33), labels[i], fill=white)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{w},{h}")
    meta.add_text("FrameAmount", str(len(SUPPORT_ICONS)))
    img.save(os.path.join(out, "support-icon.png"), pnginfo=meta)


def shrink_sheet(out, src, dst, size=(46, 34)):
    """Scales every frame of a 62x46 icon sheet to size, for the compact power list on the left of the screen."""
    img = Image.open(os.path.join(out, src))
    w, h = (int(v) for v in img.info["FrameSize"].split(","))
    n = img.width // w
    sheet = Image.new("RGBA", (size[0] * n, size[1]), (0, 0, 0, 0))
    for i in range(n):
        sheet.paste(img.crop((i * w, 0, (i + 1) * w, h)).resize(size, Image.LANCZOS), (i * size[0], 0))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{size[0]},{size[1]}")
    meta.add_text("FrameAmount", str(n))
    sheet.save(os.path.join(out, dst), pnginfo=meta)


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


def write_ability_props(out):
    """The wraith's portal (4 frames of a violet ring that swells and shrinks) and the behemoth's rock pillar, both 32x32 and
    drawn here, not cut from TGMC."""
    frames = 4
    img = Image.new("RGBA", (32 * frames, 32), (0, 0, 0, 0))
    for i in range(frames):
        layer = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        r = 11 + (i if i < 3 else 1)
        d.ellipse([16 - r // 2 - 2, 16 - r, 16 + r // 2 + 2, 16 + r], fill=(40, 10, 70, 190), outline=(200, 120, 255, 255), width=2)
        d.ellipse([16 - r // 4, 16 - r // 2, 16 + r // 4, 16 + r // 2], fill=(150, 80, 230, 150))
        img.paste(layer, (32 * i, 0))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", "32,32")
    meta.add_text("FrameAmount", str(frames))
    img.save(os.path.join(out, "wraith-portal.png"), pnginfo=meta)
    rock = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(rock)
    d.polygon([(8, 30), (5, 14), (11, 3), (20, 2), (27, 12), (25, 30)], fill=(104, 96, 88, 255), outline=(50, 46, 42, 255))
    d.polygon([(11, 3), (20, 2), (17, 16), (9, 15)], fill=(140, 132, 122, 255))
    d.line([(17, 16), (19, 30)], fill=(60, 56, 52, 255))
    rock.save(os.path.join(out, "earth-pillar.png"))
    # Resin strands that hang over a corrupted miner (32x48, the miner's own size): dark purple ropes with pale knots.
    strands = Image.new("RGBA", (32, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(strands)
    for x0, y0, x1, y1 in ((3, 44, 14, 12), (29, 44, 18, 10), (8, 46, 24, 22), (24, 46, 9, 26), (2, 30, 30, 34)):
        d.line([(x0, y0), (x1, y1)], fill=(58, 24, 78, 230), width=3)
        d.line([(x0, y0), (x1, y1)], fill=(140, 80, 170, 255), width=1)
    for x, y in ((14, 12), (18, 10), (16, 34), (9, 26), (24, 22)):
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(190, 140, 215, 255), outline=(58, 24, 78, 255))
    strands.save(os.path.join(out, "resin-strands.png"))
    # The mound a burrowed widow leaves: a low heap of dug earth.
    mound = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(mound)
    d.ellipse([3, 14, 29, 30], fill=(88, 66, 44, 255), outline=(48, 36, 24, 255))
    d.ellipse([9, 17, 23, 26], fill=(40, 28, 18, 255))
    for x, y in ((6, 20), (25, 22), (12, 15), (20, 16), (15, 28)):
        d.point((x, y), fill=(140, 110, 80, 255))
    mound.save(os.path.join(out, "burrow-mound.png"))


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


def write_rank_chevrons(out):
    """rank.png: the veterancy chevrons shown at a ranked marine's foot (WithDecoration in units.yaml), three 16x16 frames:
    one silver chevron (Veteran), two gold (Hardened), three bright gold (Elite). Drawn here, no TGMC art."""
    size = 16
    colours = ((196, 200, 206, 255), (224, 184, 80, 255), (255, 214, 72, 255))
    outline = (20, 18, 12, 255)
    sheet = Image.new("RGBA", (size * 3, size), (0, 0, 0, 0))
    for rank, colour in enumerate(colours):
        frame = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(frame)
        # Chevrons point up, stacked from the bottom, 4 px apart: a dark outline line under a coloured one.
        for k in range(rank + 1):
            y = 13 - 4 * k
            for width, fill in ((4, outline), (2, colour)):
                d.line([(2, y), (8, y - 4), (14, y)], fill=fill, width=width, joint="curve")
        sheet.paste(frame, (size * rank, 0))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{size},{size}")
    meta.add_text("FrameAmount", "3")
    sheet.save(os.path.join(out, "rank.png"), pnginfo=meta)


def draw_miner(spin=0, broken=False, glow=(120, 230, 100, 255), ring=None):
    """One drill seen from above, 128 px (scaled down by the caller). spin turns the bit (0-3); broken leaves it out of line and dark."""
    S = 128
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    concrete, concrete_dark = (72, 74, 80, 255), (38, 40, 46, 255)
    steel, steel_dark, steel_light = (122, 128, 138, 255), (46, 50, 58, 255), (166, 172, 182, 255)
    gold, gold_dark = (214, 176, 70, 255), (112, 84, 28, 255)
    d.rounded_rectangle([4, 4, 123, 123], radius=12, fill=concrete_dark)
    d.rounded_rectangle([8, 8, 119, 119], radius=10, fill=concrete)
    for bx, by in ((18, 18), (110, 18), (18, 110), (110, 110)):
        d.ellipse([bx - 5, by - 5, bx + 5, by + 5], fill=steel_dark)
        d.ellipse([bx - 2, by - 2, bx + 2, by + 2], fill=steel_light)
    if ring is not None:
        # the marker on a field: a ring around the pad, so the field shows on the map
        d.ellipse([10, 10, 117, 117], outline=ring, width=5)
    cx, cy, r = 64, 60, 36
    octagon = [(cx + r * math.cos(math.radians(22.5 + 45 * k)), cy + r * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    d.polygon(octagon, fill=steel_dark)
    d.polygon([(x * 0.9 + cx * 0.1, y * 0.9 + cy * 0.1) for x, y in octagon], fill=steel)
    d.line([(cx - r + 6, cy - 6), (cx - 6, cy - r + 6)], fill=steel_light, width=3)  # bevel highlight
    d.line([(cx, cy + r - 2), (cx, 108)], fill=steel_dark, width=7)  # power cable down to the pad
    bx, by = (cx + 3, cy - 2) if broken else (cx, cy)
    d.ellipse([bx - 15, by - 15, bx + 15, by + 15], fill=gold_dark)
    d.ellipse([bx - 12, by - 12, bx + 12, by + 12], fill=(60, 60, 64, 255) if broken else gold)
    spokes = (0, 60, 120) if not broken else (0, 90)
    for k in spokes:
        a = math.radians(spin * 20 + k)
        d.line([(bx - 11 * math.cos(a), by - 11 * math.sin(a)), (bx + 11 * math.cos(a), by + 11 * math.sin(a))], fill=gold_dark, width=4)
    d.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill=steel_dark)  # the spindle
    d.ellipse([cx + 24, cy - 33, cx + 34, cy - 23], fill=glow)  # status light on the housing
    return img


def write_tgmc_miner_art(out, tgmc):
    """The marine miner and the ore field cut from TGMC's own drill (icons/obj/mining_drill.dmi, 32x48): the running drill (4 frames) and the
    icon, and the broken one (2 frames) standing in a pulsing ring, so the field shows on the map. Same file names as write_miner_art."""
    sheet = tgmc_dmi.Dmi(os.path.join(tgmc, "icons", "obj", "mining_drill.dmi"))

    def frames(state):
        return [(f[0] if isinstance(f, list) else f).convert("RGBA") for f in sheet.frames(state)]

    running, broken = frames("mining_drill_active_"), frames("mining_drill_error_")
    w, h = running[0].size

    def strip(images, name, under=None):
        out_img = Image.new("RGBA", (w * len(images), h), (0, 0, 0, 0))
        for i, im in enumerate(images):
            if under is not None:
                ring = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                ImageDraw.Draw(ring).ellipse([0, h - w, w - 1, h - 1], outline=under[i], width=2)
                out_img.paste(ring, (w * i, 0), ring)
            out_img.paste(im, (w * i, 0), im)
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", f"{w},{h}")
        meta.add_text("FrameAmount", str(len(images)))
        out_img.save(os.path.join(out, name), pnginfo=meta)

    strip(running, "miner.png")
    strip(broken, "miner-field.png", under=((255, 210, 60, 255), (255, 210, 60, 110)))
    icon = running[0].copy()
    fit = min(1, 44 / max(icon.size))
    icon = tgmc_dmi.nearest(icon, (round(icon.width * fit), round(icon.height * fit)))
    icon.save(os.path.join(out, "miner-icon.png"))


def write_miner_upgrade_icons(out):
    """The miner upgrades' palette icons (tgmc/sequences/miner.yaml): the miner on the same dark card as the other upgrades (build_sprites.cameo),
    with a gold plus in the corner for the deep-core drills and a blue shield for the reinforced housings."""
    from build_sprites import cameo
    dark = (16, 16, 16, 255)
    plus = cameo(Image.open(os.path.join(out, "miner-icon.png")))
    d = ImageDraw.Draw(plus)
    for off, fill in ((1, dark), (0, (255, 206, 64, 255))):
        d.rectangle([46 - off, 32 - off, 58 + off, 36 + off], fill=fill)
        d.rectangle([50 - off, 28 - off, 54 + off, 40 + off], fill=fill)
    plus.save(os.path.join(out, "upgrade-miner-drills.png"))
    shield = cameo(Image.open(os.path.join(out, "miner-icon.png")))
    d = ImageDraw.Draw(shield)
    d.polygon([(45, 27), (59, 27), (59, 35), (52, 42), (45, 35)], fill=dark)
    d.polygon([(47, 29), (57, 29), (57, 34), (52, 39), (47, 34)], fill=(84, 140, 214, 255))
    shield.save(os.path.join(out, "upgrade-miner-housing.png"))


# upgrade actor -> (whose icon it borrows from build_sprites' sprites/<name>-icon.png, badge text, badge colour)
BADGE_UPGRADES = {
    "upgrade-mutation-shell": ("defender", "SHL", (84, 140, 214)),
    "upgrade-mutation-spur": ("ravager", "SPR", (255, 90, 90)),
    "upgrade-mutation-veil": ("warlock", "VEL", (200, 120, 255)),
    "upgrade-primordial-1": ("hunter", "P1", (255, 206, 64)),
    "upgrade-primordial-2": ("king", "P2", (255, 206, 64)),
    "upgrade-som-cells": ("som_trooper", "+20", (255, 122, 24)),
    "upgrade-som-blink": ("som_blademan", "10", (120, 200, 255)),
    "upgrade-som-shield": ("som_veteran", "SHD", (84, 140, 214)),
    "upgrade-attach-barrel": ("rifleman", "RNG", (120, 200, 255)),
    "upgrade-attach-bayonet": ("rifleman", "BAY", (220, 220, 220)),
    "upgrade-attach-harness": ("rifleman", "RLD", (255, 206, 64)),
    "upgrade-attach-scope": ("sniper", "SCP", (120, 200, 255)),
    "upgrade-plasteel-cades": ("cade", "x2", (84, 140, 214)),
    "upgrade-sentry": ("sentry-turret", "UP", (255, 206, 64)),
    "upgrade-thick-weeds": ("weed-node", "+HP", (110, 230, 110)),
    "upgrade-sticky-weeds": ("weed-node", "SLW", (200, 120, 255)),
    "upgrade-fast-weeds": ("weed-node", ">>", (255, 206, 64)),
    "upgrade-hardened-resin": ("resin-wall", "+", (84, 140, 214)),
    "upgrade-turret-reach": ("resin-turret", "RNG", (120, 200, 255)),
}


def write_badge_upgrade_icons(out):
    """Palette icons for BADGE_UPGRADES (tgmc/sequences/misc.yaml): the borrowed icon with a short badge in the lower right corner.
    Without the borrowed icon (no TGMC checkout) the card is plain dark, so the build still has every file."""
    for name, (base, text, colour) in BADGE_UPGRADES.items():
        path = os.path.join(out, "sprites", f"{base}-icon.png")
        # build_sprites pads its icon sheets to a power of two: the icon itself is the first 62x46 frame.
        icon = Image.open(path).convert("RGBA").crop((0, 0, 62, 46)) if os.path.exists(path) else Image.new("RGBA", (62, 46), (24, 24, 28, 255))
        d = ImageDraw.Draw(icon)
        w = 6 * len(text) + 5
        d.rectangle([icon.width - w - 2, icon.height - 13, icon.width - 2, icon.height - 2], fill=(16, 16, 16, 235), outline=colour + (255,))
        d.text((icon.width - w + 1, icon.height - 13), text, fill=colour + (255,))
        icon.save(os.path.join(out, f"{name}.png"))


def sweep_actors():
    """Every actor of units.yaml and structures.yaml (templates, upgrades and the few that cannot stand on a map left out), six
    cells apart on a grid, for the crash sweep map. Ore fields and a platinum vein go in too."""
    import re
    rules = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tgmc", "rules")
    names = []
    for name in ("units.yaml", "structures.yaml"):
        names += re.findall(r"^([a-z][\w-]*):", open(os.path.join(rules, name), encoding="utf-8").read(), re.M)
    names = [n for n in names if n not in SWEEP_SKIP]
    placed = [(n, "Marines", 6 + (i % 14) * 6, 6 + (i // 14) * 6, 0) for i, n in enumerate(names)]
    row = 6 + (len(names) // 14 + 1) * 6
    return placed + [("miner-field", "Neutral", 6, row, 0), ("miner-field", "Neutral", 12, row, 0), ("platinum-vein", "Neutral", 12, row, 0)]


# Not for the sweep map: actors that are never placed on their own.
SWEEP_SKIP = set()


def write_miner_art(out):
    """The marine miner and the ore field, drawn here rather than cut from TGMC's 32x48 drill (too tall for a cell). Both are one cell
    (32 px) and the miner's icon is 44 px. miner.png: 4 frames of the spinning bit. miner-icon.png: the sidebar picture.
    miner-field.png: 2 frames of the broken drill with a pulsing ring, so the field shows on the map. The sequences are in tgmc/sequences/miner.yaml."""
    size = 32
    spin = [draw_miner(spin=i).resize((size, size), Image.LANCZOS) for i in range(4)]
    strip = Image.new("RGBA", (size * 4, size), (0, 0, 0, 0))
    for i, f in enumerate(spin):
        strip.paste(f, (size * i, 0), f)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{size},{size}")
    meta.add_text("FrameAmount", "4")
    strip.save(os.path.join(out, "miner.png"), pnginfo=meta)
    draw_miner(spin=0).resize((44, 44), Image.LANCZOS).save(os.path.join(out, "miner-icon.png"))

    field = Image.new("RGBA", (size * 2, size), (0, 0, 0, 0))
    for i, ring in enumerate(((255, 210, 60, 255), (255, 210, 60, 110))):
        f = draw_miner(spin=0, broken=True, glow=(255, 150, 40, 255), ring=ring).resize((size, size), Image.LANCZOS)
        field.paste(f, (size * i, 0), f)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{size},{size}")
    meta.add_text("FrameAmount", "2")
    field.save(os.path.join(out, "miner-field.png"), pnginfo=meta)


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

# Evac (mission-evac.lua): the marine base in the west, two ore fields inside its sentries and two out in the open. The landing
# zone is the dirt square in the east; the Alamo lands on it.
EVAC = [
    ("cryo-pod", "Marines", 7, 24, 512), ("vendor", "Marines", 10, 22, 512), ("vendor", "Marines", 10, 26, 512),
    ("sentry-turret", "Marines", 15, 20, 256), ("sentry-turret", "Marines", 15, 28, 256),
    ("cade", "Marines", 17, 22, 0), ("cade", "Marines", 17, 23, 0), ("cade", "Marines", 17, 25, 0), ("cade", "Marines", 17, 26, 0),
    ("miner-field", "Neutral", 12, 16, 0), ("miner-field", "Neutral", 12, 32, 0),
    ("miner-field", "Neutral", 30, 6, 0), ("miner-field", "Neutral", 30, 42, 0),
    ("rifleman", "Marines", 12, 23, 256), ("rifleman", "Marines", 12, 25, 256), ("rifleman", "Marines", 13, 22, 256),
    ("rifleman", "Marines", 13, 26, 256), ("medic", "Marines", 11, 24, 256), ("engineer", "Marines", 10, 24, 256),
    ("engineer", "Marines", 9, 24, 256), ("resin-silo", "Xenos", 62, 46, 0),
]
# The xenos see the whole marine base (the agreed exception to fair fog), so each wave can pick the weak spot.
EVAC_RULES = "Player:\n\tThreatMemory:\n\t\tFullVision: true\n"


def _base_actors(spawns):
    """Landing Zone's two bases, moved to the map's first two spawn points (marines, then xenos)."""
    (mx, my), (xx, xy) = spawns[:2]
    return [(n, o, x + (xx - 33 if o == "Xenos" else mx - 6), y + (xy - 13 if o == "Xenos" else my - 14), f) for n, o, x, y, f in LANDING_ZONE]


def _scramble(a, b):
    """A fixed scramble of two numbers, so a map builds the same every time."""
    n = (a * 374761393 + b * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return n ^ (n >> 16)


def _pad(spawns, x, y):
    """The landing pad north of every base, where the Alamo of the landing intro sets down (FactionStart's TransportOffset is 13 cells
    north of the base; the pad is the one shell_ground draws for the menu). 0 off the pads, 1 on a pad's edge, 2 inside one."""
    for sx, sy in spawns:
        x0, x1, y0, y1 = sx - 5, sx + 5, max(1, sy - 23), sy - 2
        if x0 <= x <= x1 and y0 <= y <= y1:
            return 1 if x in (x0, x1) or y in (y0, y1) else 2
    return 0


# The marines' camo for a theme (TgmcCamo), and what the theme scatters: (props that block, props to walk over), see build_maptiles.PROPS.
THEME_CAMO = {"jungle": "jungle", "desert": "", "snow": "ice", "lava": ""}
THEME_PROPS = {"jungle": (("rock", "boulder"), ("bush", "fern", "leaves")), "desert": (("cactus", "boulder"), ("drygrass", "shortcactus", "leafy")),
               "snow": (("boulder",), ("snowbush", "snowgrass")), "lava": (("basalt",), ("lavarocks",))}


def built_map(name, m, tiles):
    """A built map's ground function in its theme's TGMC pictures, and its neutral actors: ore fields, cover and scattered props.
    `tiles` is build_maptiles.prepare's result, or None without a TGMC checkout: then the flat templates, a dirt pad and no props."""
    spawns, (w, h) = m["spawns"], m["size"]
    ids = tiles.themes[m["theme"]] if tiles else None

    def cells(rects):
        return {(x, y) for x0, y0, x1, y1 in rects for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    walls, fences = cells(m.get("walls") or ()), cells(m.get("fences", ()))

    def raw(x, y):
        return (WALL, 0) if (x, y) in walls else m["ground"](x, y)
    roles = {GRASS: "ground", DIRT: "road", WATER: "water", FORD: "ford"}

    def ground(x, y):
        pad, kind = _pad(spawns, x, y), raw(x, y)[0]
        if not ids:
            return (DIRT if pad else kind), 0
        role = ("edge" if pad == 1 else "pad") if pad else roles.get(kind)
        if kind == WALL:  # TGMC's wall of the theme, joined to the wall cells beside it
            return ids["wall"][sum(bit for bit, (dx, dy) in ((1, (0, -1)), (2, (0, 1)), (4, (1, 0)), (8, (-1, 0))) if raw(x + dx, y + dy)[0] == WALL)], 0
        if role is None:  # rock: the repo's joined cave pieces
            return kind, 0
        return ids[role][_scramble(x, y) % len(ids[role])], 0

    def open_ground(x, y):
        return 1 <= x < w - 1 and 1 <= y < h - 1 and (x, y) not in fences and (_pad(spawns, x, y) or raw(x, y)[0] in (GRASS, DIRT, FORD))

    # Every base and every ore field must be reachable on foot from the first base.
    reach, todo = {spawns[0]}, [spawns[0]]
    while todo:
        x, y = todo.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in reach and open_ground(*n):
                reach.add(n)
                todo.append(n)
    for spawn in spawns:
        assert spawn in reach, f"{name}: the base at {spawn} cannot be reached from the base at {spawns[0]}"
    for x, y in m["fields"]:
        assert raw(x, y)[0] in (GRASS, DIRT) and not _pad(spawns, x, y), f"{name}: the ore field at {x},{y} is not on open ground"
        assert any(n in reach for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))), f"{name}: no way to the ore field at {x},{y}"
        assert all(max(abs(x - sx), abs(y - sy)) >= 5 for sx, sy in spawns), f"{name}: the ore field at {x},{y} sits in a base"
    actors = [("miner-field", "Neutral", x, y, 0) for x, y in m["fields"]]
    # Platinum (pays half as much again, see platinum-vein in mapobjects.yaml) lies under the contested fields: those about as far
    # from their nearest base as from the next one (within a quarter).
    for x, y in m["fields"]:
        near, next_one = sorted(max(abs(x - sx), abs(y - sy)) for sx, sy in spawns)[:2]
        if near * 4 >= next_one * 3:
            actors.append(("platinum-vein", "Neutral", x, y, 0))
    # The Distress Signal points, clear of the fields, fences and hand-placed cover; scattered props keep off them below.
    busy = set(m["fields"]) | set(cells(m.get("fences", ()))) | {(x, y) for _, x, y in m.get("cover", ())}
    objective = distress_objective(reach, (), (), spawns, busy)
    actors += objective
    if not tiles:
        return ground, actors
    taken = set(m["fields"]) | {(x, y) for _, _, x, y, _ in objective}
    # Fence lines: a rectangle taller than wide runs north-south. They stand with no wall broken in the reachability check above.
    for x0, y0, x1, y1 in m.get("fences", ()):
        for x, y in sorted(cells([(x0, y0, x1, y1)])):
            assert raw(x, y)[0] in (GRASS, DIRT, FORD) and not _pad(spawns, x, y) and (x, y) not in taken, f"{name}: fence at {x},{y} is not on free open ground"
            taken.add((x, y))
            actors.append((tiles.props["fence_ns" if y1 - y0 > x1 - x0 else "fence_ew"], "Neutral", x, y, 0))
    for prop, x, y in m.get("cover", ()):
        assert raw(x, y)[0] in (GRASS, DIRT) and not _pad(spawns, x, y) and (x, y) not in taken, f"{name}: {prop} at {x},{y} is not on free open ground"
        taken.add((x, y))
        actors.append((tiles.props[prop], "Neutral", x, y, 0))
    # Scattered props, on the theme's plain ground only: clear of the bases, the pads, the roads and the ore fields. One that
    # blocks stands only in the open (plain ground two cells around), so it never plugs a trail.
    blocking, plain = THEME_PROPS[m["theme"]]
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            if raw(x, y)[0] != GRASS or _pad(spawns, x, y) or any(max(abs(x - sx), abs(y - sy)) <= 8 for sx, sy in spawns) \
                    or any(abs(x - fx) <= 1 and abs(y - fy) <= 1 for fx, fy in taken):
                continue
            n = _scramble(x * 7 + 3, y * 13 + 1)
            if n % 90 == 0 and all(raw(x + dx, y + dy)[0] == GRASS and not _pad(spawns, x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3)):
                actors.append((tiles.props[blocking[n // 90 % len(blocking)]], "Neutral", x, y, 0))
            elif n % 30 == 1:
                actors.append((tiles.props[plain[n // 30 % len(plain)]], "Neutral", x, y, 0))
    return ground, actors


# Operation Hot Drop, the campaign (write_tgmc_map's `mission`): TGMC's own maps, shrunk, with TGMC's game modes.
CAMPAIGN = {
    "campaign-1-distress": dict(map="lv-624", objective="distress", title="Hot Drop 1: Distress Signal",
        brief="LV-624 has gone silent. Land, decode the three nuke disk terminals in the colony and arm the nuclear device before the hive grows."),
    "campaign-2-blackout": dict(map="ice-colony", objective="distress", night=True, title="Hot Drop 2: Blackout",
        brief="The hive has cut the power on Ice Colony. Repair the geothermal generators to light the dark, then decode the disks and arm the nuke."),
    "campaign-3-crash": dict(map="big-red", objective="crash", title="Hot Drop 3: Crash",
        brief="The ship has come down on Big Red. You have twenty-five minutes to decode the disks and set off the nuke before the hive overruns the site."),
}


# The maps built by hand. spawns: the marine base, the xeno base, then any further bases (a map with four is a four-player map).
# fields: the ore fields (miner-field): two safe ones by each base and contested ones between them (platinum goes under the furthest). cover: (prop, x, y) placed by hand. brief: the line under the map picker's preview.
# walls, fences: rectangles (x0, y0, x1, y1) of breakable wall cells and of fence. Each closes a shortcut, never the only way: the
# bases and fields must be reachable with all of them standing. A map whose ground function draws walls itself has walls=[].
SKIRMISH_MAPS = {
    "landing-zone": dict(walls=[(15, 10, 15, 11), (15, 16, 15, 17), (24, 10, 24, 11), (24, 16, 24, 17)], fences=[(17, 10, 17, 11), (22, 16, 22, 17)],
        title="Landing Zone", size=(40, 28), spawns=[(6, 14), (33, 13)], ground=landing_zone_ground, theme="jungle", weather="clear",
                         fields=[(11, 22), (28, 22), (12, 6), (27, 6), (21, 14)], brief="Jungle river with three fords. Short and direct: the first map to learn on."),
    "canyon-run": dict(walls=[(25, 5, 26, 10), (25, 17, 26, 22)], fences=[(26, 3, 26, 4), (26, 23, 26, 24)],
        title="Canyon Run", size=(52, 28), spawns=[(6, 14), (45, 13)], ground=canyon_run_ground, theme="desert", weather="dust",
                       fields=[(13, 23), (38, 23), (13, 5), (38, 5), (26, 14)], brief="Desert canyon: one wide lane down the middle, a narrow trail along each wall."),
    "jungle-crossing": dict(walls=[(22, 23, 22, 26)], fences=[(22, 1, 22, 4)],
        title="Jungle Crossing", size=(44, 28), spawns=[(6, 14), (37, 13)], ground=jungle_crossing_ground, theme="jungle", weather="rain",
                            fields=[(13, 20), (30, 20), (13, 7), (30, 7), (20, 4), (21, 24)], brief="A lake in the rain: wade the causeway or go round by either shore."),
    "close-quarters": dict(walls=[(15, 2, 15, 5), (18, 2, 18, 5)], fences=[(15, 22, 15, 25), (18, 22, 18, 25)],
        title="Close Quarters", size=(34, 28), spawns=[(6, 14), (27, 13)], ground=close_quarters_ground, theme="snow", weather="snow",
                           fields=[(10, 23), (23, 23), (12, 4), (21, 3), (18, 14)], cover=[("barricade", 14, 12), ("barricade", 14, 15), ("barricade", 19, 12), ("barricade", 19, 15)],
                           brief="Bases thirteen cells apart across a frozen stream. Over in minutes."),
    "great-plains": dict(walls=[(34, 13, 37, 13), (26, 21, 29, 21)], fences=[(29, 10, 31, 10), (33, 29, 35, 29)],
        title="Great Plains", size=(64, 40), spawns=[(6, 20), (57, 19)], ground=great_plains_ground, theme="jungle", weather="clear",
                         fields=[(12, 30), (51, 30), (30, 12), (34, 27), (12, 10), (51, 10)],
                         cover=[("crate", 36, 15), ("ammocrate", 37, 15), ("supplycrate", 27, 22), ("crate", 28, 22)],
                         brief="Open grass and ponds, six ore fields: a long walk, so economy and walls decide it."),
    "twin-rivers": dict(walls=[(24, 9, 24, 13), (39, 40, 39, 44)], fences=[(24, 35, 24, 39), (39, 4, 39, 8)],
        title="Twin Rivers", size=(64, 48), spawns=[(6, 24), (57, 23)], ground=twin_rivers_ground, theme="jungle", weather="rain",
                        fields=[(12, 34), (51, 34), (32, 20), (32, 28), (12, 14), (51, 14)], brief="Two rivers whose fords do not line up; two ore fields on the island between."),
    "quarry-pit": dict(walls=[(24, 19, 25, 19), (39, 19, 40, 19), (24, 29, 25, 29), (39, 29, 40, 29)], fences=[(30, 15, 34, 15), (30, 33, 34, 33)],
        title="Quarry Pit", size=(64, 48), spawns=[(6, 24), (57, 23)], ground=quarry_pit_ground, theme="desert", weather="dust",
                       fields=[(12, 34), (51, 34), (32, 21), (12, 14), (51, 14)], brief="A rock ring round a pit with an ore field in it: hold the pit, see all four roads."),
    "broken-bridge": dict(walls=[(22, 10, 22, 13), (41, 36, 42, 38)], fences=[(37, 17, 39, 17)],
        title="Broken Bridge", size=(64, 48), spawns=[(6, 24), (57, 23)], ground=broken_bridge_ground, theme="lava", weather="ash",
                          fields=[(12, 34), (51, 34), (30, 30), (38, 18), (12, 14), (51, 14)], brief="A rift of lava with three bridges, or the long way round its ends."),
    "desert-outpost": dict(walls=[], fences=[(35, 22, 36, 22), (35, 35, 36, 35)],
        title="Desert Outpost", size=(72, 56), spawns=[(8, 29), (63, 28)], ground=desert_outpost_ground, theme="desert", weather="dust",
                           fields=[(33, 25), (38, 25), (33, 32), (12, 36), (59, 36), (14, 20), (57, 20)], cover=[("crate", 34, 31), ("ammocrate", 37, 33), ("supplycrate", 39, 26)],
                           brief="A walled compound on the road holds three ore fields. Its walls come down to heavy weapons."),
    "ice-shelf": dict(walls=[(18, 18, 19, 19), (52, 30, 53, 31)], fences=[(17, 9, 17, 14), (54, 9, 54, 14)],
        title="Ice Shelf", size=(72, 48), spawns=[(8, 25), (63, 24)], ground=ice_shelf_ground, theme="snow", weather="snow",
                      fields=[(12, 33), (59, 33), (36, 16), (36, 32), (14, 15), (57, 15)], brief="Two ice walls with three passes each; frozen lakes slow whoever crosses them."),
    "lava-fields": dict(walls=[(27, 45, 27, 47), (46, 45, 46, 47)], fences=[(27, 9, 27, 11), (46, 9, 46, 11)],
        title="Lava Fields", size=(72, 56), spawns=[(8, 29), (63, 28)], ground=lava_fields_ground, theme="lava", weather="ash", night=True,
                        fields=[(12, 38), (59, 38), (36, 22), (36, 34), (14, 18), (57, 18)], brief="Night and falling ash. Two rivers of lava, three bridges over each."),
    "crossroads": dict(walls=[], fences=[(47, 40, 48, 40), (47, 55, 48, 55)],
        title="Crossroads", size=(96, 96), spawns=[(14, 27), (81, 78), (81, 27), (14, 78)], ground=crossroads_ground, theme="jungle", weather="clear",
                       fields=[(43, 43), (52, 43), (43, 52), (52, 52), (22, 33), (73, 33), (22, 84), (73, 84)],
                       cover=[("crate", 45, 45), ("ammocrate", 50, 45), ("supplycrate", 45, 50), ("crate", 50, 50)],
                       brief="Four bases. Two roads cross in a walled yard with four ore fields."),
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
    "scenario-stance": _scenario("test-stance", [
        ("rifleman", "Marines", 10, 10, 512),
        ("runner", "Xenos", 13, 10, 0),
        ("rifleman", "Marines", 10, 20, 512),
        ("runner", "Xenos", 13, 20, 0),
    ]),
    "scenario-retreat": _scenario("test-retreat", [
        ("rifleman", "Marines", 4, 4, 512),
        ("cryo-pod", "Marines", 16, 16, 0),
    ]),
    "scenario-retreat-none": _scenario("test-retreat-none", [
        ("rifleman", "Marines", 4, 4, 512),
    ]),
    "scenario-queued-ability": _scenario("test-queued-ability", [
        ("squad_leader", "Marines", 4, 10, 256),
    ]),
    # Evac (see scenarios/test-evac.lua): one case per map, set by an evac-case-*.lua beside the test.
    "scenario-evac-target": {"scripts": ("mission-evac", "test-evac", "evac-case-target"), "drop_conquest": True, "size": (64, 48), "ground": "evac",
                          "extra_rules": EVAC_RULES, "actors": [
        ("cryo-pod", "Marines", 7, 24, 512), ("resin-silo", "Xenos", 62, 46, 0), ("sentry-turret", "Marines", 9, 21, 0), ("sentry-turret", "Marines", 9, 27, 0), ("sentry-turret", "Marines", 5, 24, 0), ("miner-field", "Neutral", 30, 8, 0), ("miner", "Marines", 30, 8, 0), ("miner-field", "Neutral", 30, 40, 0), ("miner", "Marines", 30, 40, 0), ("sentry-turret", "Marines", 28, 39, 0), ("sentry-turret", "Marines", 32, 39, 0), ("sentry-turret", "Marines", 30, 37, 0)
    ]},
    "scenario-evac-payout": {"scripts": ("mission-evac", "test-evac", "evac-case-payout"), "drop_conquest": True, "size": (64, 48), "ground": "evac",
                          "extra_rules": EVAC_RULES, "actors": [
        ("cryo-pod", "Marines", 7, 24, 512), ("resin-silo", "Xenos", 62, 46, 0), 
    ]},
    "scenario-evac-board": {"scripts": ("mission-evac", "test-evac", "evac-case-board"), "drop_conquest": True, "size": (64, 48), "ground": "evac",
                          "extra_rules": EVAC_RULES, "actors": [
        ("cryo-pod", "Marines", 7, 24, 512), ("resin-silo", "Xenos", 62, 46, 0), ("rifleman", "Marines", 36, 24, 256)
    ]},
    "scenario-evac-empty": {"scripts": ("mission-evac", "test-evac", "evac-case-empty"), "drop_conquest": True, "size": (64, 48), "ground": "evac",
                          "extra_rules": EVAC_RULES, "actors": [
        ("cryo-pod", "Marines", 7, 24, 512), ("resin-silo", "Xenos", 62, 46, 0), 
    ]},
    "scenario-evac-early": {"scripts": ("mission-evac", "test-evac", "evac-case-early"), "drop_conquest": True, "size": (64, 48), "ground": "evac",
                          "extra_rules": EVAC_RULES, "actors": [
        ("cryo-pod", "Marines", 7, 24, 512), ("resin-silo", "Xenos", 62, 46, 0), ("rifleman", "Marines", 36, 24, 256)
    ]},
    "scenario-evac-full": {"scripts": ("mission-evac", "test-evac", "evac-case-full"), "drop_conquest": True, "size": (64, 48), "ground": "evac",
                           "extra_rules": EVAC_RULES + "cryo-pod:\n\tHealth:\n\t\tHP: 1000000\nvendor:\n\tHealth:\n\t\tHP: 1000000\n", "actors": EVAC},
    # The castes added from TGMC each use their first ability on a marine (see scenarios/test-new-castes.lua).
    "scenario-new-castes": {"scripts": ("test-new-castes",), "size": (32, 56), "drop_conquest": True,
                            "extra_rules": "rifleman:\n\tHealth:\n\t\tHP: 3000\nking:\n\tPlasma:\n\t\tStartPercent: 100\nbehemoth:\n\tPlasma:\n\t\tStartPercent: 100\n", "actors": [
        ("baneling", "Xenos", 10, 3, 256), ("rifleman", "Marines", 12, 3, 768), ("defender", "Xenos", 10, 7, 256), ("rifleman", "Marines", 12, 7, 768), ("beetle", "Xenos", 10, 11, 256), ("rifleman", "Marines", 12, 11, 768), ("gorger", "Xenos", 10, 15, 256), ("rifleman", "Marines", 12, 15, 768), ("puppeteer", "Xenos", 10, 19, 256), ("rifleman", "Marines", 12, 19, 768), ("pyrogen", "Xenos", 10, 23, 256), ("rifleman", "Marines", 12, 23, 768), ("scorpion", "Xenos", 10, 27, 256), ("rifleman", "Marines", 12, 27, 768), ("dragon", "Xenos", 10, 31, 256), ("rifleman", "Marines", 12, 31, 768), ("king", "Xenos", 10, 35, 256), ("rifleman", "Marines", 12, 35, 768), ("mantis", "Xenos", 10, 43, 256), ("rifleman", "Marines", 12, 43, 768), ("hivelord", "Xenos", 10, 47, 256), ("nymph", "Xenos", 12, 47, 768), ("behemoth", "Xenos", 10, 51, 256), ("rifleman", "Marines", 12, 51, 768),
        ("cryo-pod", "Marines", 28, 52, 0), ("resin-silo", "Xenos", 28, 2, 0),
    ]},
    # The abilities added to follow TGMC's kits: each caste uses them on the marine beside it (see scenarios/test-caste-kits.lua).
    "scenario-caste-kits": {"scripts": ("test-caste-kits",), "size": (32, 46), "drop_conquest": True,
                            "extra_rules": "rifleman:\n\tHealth:\n\t\tHP: 3000\ncrusher:\n\tPlasma:\n\t\tStartPercent: 100\nravager:\n\tPlasma:\n\t\tStartPercent: 100\ndefender:\n\tPlasma:\n\t\tStartPercent: 100\nwarlock:\n\tPlasma:\n\t\tStartPercent: 100\npyrogen:\n\tPlasma:\n\t\tStartPercent: 100\nwidow:\n\tPlasma:\n\t\tStartPercent: 100\ncarrier:\n\tPlasma:\n\t\tStartPercent: 100\npuppeteer:\n\tPlasma:\n\t\tStartPercent: 100\n", "actors": [
        ("crusher", "Xenos", 10, 3, 768), ("rifleman", "Marines", 11, 3, 256), ("ravager", "Xenos", 10, 8, 768), ("rifleman", "Marines", 11, 8, 256), ("defender", "Xenos", 10, 13, 768), ("rifleman", "Marines", 11, 13, 256), ("warlock", "Xenos", 10, 18, 768), ("rifleman", "Marines", 11, 18, 256), ("pyrogen", "Xenos", 10, 23, 768), ("rifleman", "Marines", 11, 23, 256), ("widow", "Xenos", 10, 28, 768), ("rifleman", "Marines", 11, 28, 256), ("carrier", "Xenos", 10, 33, 768), ("rifleman", "Marines", 11, 33, 256), ("puppeteer", "Xenos", 10, 38, 768), ("rifleman", "Marines", 11, 38, 256),
        ("cryo-pod", "Marines", 28, 42, 0), ("resin-silo", "Xenos", 28, 2, 0),
    ]},
    # The xeno bot uses the new kits on its own: each caste beside two riflemen that hold fire, with only the bot's ability module at work
    # (see scenarios/test-ai-caste-kits.lua).
    "scenario-ai-caste-kits": {"scripts": ("test-ai-caste-kits",), "size": (32, 46), "drop_conquest": True, "xeno_bot": "skirmish",
                               "extra_rules": "Player:\n\t-SquadManagerBotModule@xenos-easy:\n\t-SquadManagerBotModule@xenos-normal:\n\t-SquadManagerBotModule@xenos-hard:\n\t-SquadManagerBotModule@xenos-rusher:\n\t-SquadManagerBotModule@xenos-turtle:\n\t-EvolveBotModule@xenos:\n\t-RetreatBotModule@xenos:\n\t-ScoutBotModule@xenos:\n\t-FieldBotModule@xenos:\n\t-DefendBotModule@xenos:\n\t-DefendBotModule@xenos-turtle:\n\t-RaidBotModule@xenos:\n\t-RaidBotModule@xenos-raider:\n\t-AttackTargetBotModule@xenos:\n\t-WeedDroneBotModule@xenos:\n\t-UnitBuilderBotModule@skirmish:\nrifleman:\n\tHealth:\n\t\tHP: 3000\ncrusher:\n\tPlasma:\n\t\tStartPercent: 100\nravager:\n\tPlasma:\n\t\tStartPercent: 100\ndefender:\n\tPlasma:\n\t\tStartPercent: 100\nwarlock:\n\tPlasma:\n\t\tStartPercent: 100\npyrogen:\n\tPlasma:\n\t\tStartPercent: 100\nwidow:\n\tPlasma:\n\t\tStartPercent: 100\ncarrier:\n\tPlasma:\n\t\tStartPercent: 100\npuppeteer:\n\tPlasma:\n\t\tStartPercent: 100\n", "actors": [
        ("crusher", "Xenos", 10, 3, 768), ("rifleman", "Marines", 11, 3, 256), ("rifleman", "Marines", 11, 4, 256), ("ravager", "Xenos", 10, 8, 768), ("rifleman", "Marines", 11, 8, 256), ("rifleman", "Marines", 11, 9, 256), ("defender", "Xenos", 10, 13, 768), ("rifleman", "Marines", 11, 13, 256), ("rifleman", "Marines", 11, 14, 256), ("warlock", "Xenos", 10, 18, 768), ("rifleman", "Marines", 11, 18, 256), ("rifleman", "Marines", 11, 19, 256), ("pyrogen", "Xenos", 10, 23, 768), ("rifleman", "Marines", 11, 23, 256), ("rifleman", "Marines", 11, 24, 256), ("widow", "Xenos", 10, 28, 768), ("rifleman", "Marines", 11, 28, 256), ("rifleman", "Marines", 11, 29, 256), ("carrier", "Xenos", 10, 33, 768), ("rifleman", "Marines", 11, 33, 256), ("rifleman", "Marines", 11, 34, 256), ("puppeteer", "Xenos", 10, 38, 768), ("rifleman", "Marines", 11, 38, 256), ("rifleman", "Marines", 11, 39, 256),
        ("cryo-pod", "Marines", 28, 42, 0), ("resin-silo", "Xenos", 28, 2, 0),
    ]},
    # The widow keeps at most five spiderlings (see scenarios/test-spawn-limit.lua): no cooldown or plasma cost here, so only the limit stops her.
    "scenario-spawn-limit": {"scripts": ("test-spawn-limit",), "size": (32, 24), "drop_conquest": True,
                             "extra_rules": "widow:\n\tActiveAbility@abilityspiderling:\n\t\tCooldown: 0\n\t\tPlasmaCost: 0\n", "actors": [
        ("widow", "Xenos", 10, 10, 768), ("cryo-pod", "Marines", 2, 2, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # A destroyed vehicle leaves its wreck (see scenarios/test-vehicle-wrecks.lua).
    "scenario-vehicle-wrecks": {"scripts": ("test-vehicle-wrecks",), "size": (32, 24), "drop_conquest": True, "actors": [
        ("tank", "Marines", 6, 6, 256), ("apc", "Marines", 12, 6, 256), ("som-tank", "Marines", 18, 6, 256),
        ("cryo-pod", "Marines", 2, 20, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # The vehicles from TGMC: two tanks shoot, a rifleman rides the APC (see scenarios/test-vehicles.lua).
    "scenario-vehicles": {"scripts": ("test-vehicles",), "size": (32, 24), "drop_conquest": True,
                          "extra_rules": "crusher:\n\tHealth:\n\t\tHP: 20000\n", "actors": [
        ("tank", "Marines", 6, 6, 256), ("crusher", "Xenos", 14, 6, 768), ("som-tank", "Marines", 6, 14, 256), ("crusher", "Xenos", 14, 14, 768),
        ("apc", "Marines", 6, 20, 256), ("rifleman", "Marines", 10, 20, 256), ("cryo-pod", "Marines", 2, 2, 0), ("resin-silo", "Xenos", 28, 2, 0),
    ]},
    # A raided miner warns its owner once (see scenarios/test-raid-warning.lua).
    "scenario-raid-warning": {"scripts": ("test-raid-warning",), "drop_conquest": True, "extra_rules": "miner:\n\tHealth:\n\t\tHP: 3000\n", "actors": [
        ("miner-field", "Neutral", 10, 10, 0), ("miner", "Marines", 10, 10, 0), ("runner", "Xenos", 13, 10, 0),
        ("cryo-pod", "Marines", 3, 19, 0), ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    # The town bell (see scenarios/test-recall.lua): units near a far miner run home; one outside the radius stays.
    "scenario-recall": {"scripts": ("test-recall",), "drop_conquest": True, "size": (64, 40), "actors": [
        ("cryo-pod", "Marines", 6, 20, 0), ("miner-field", "Neutral", 40, 20, 0), ("miner", "Marines", 40, 20, 0),
        ("rifleman", "Marines", 41, 21, 0), ("rifleman", "Marines", 39, 21, 0), ("engineer", "Marines", 41, 19, 0),
        ("rifleman", "Marines", 40, 5, 0), ("resin-silo", "Xenos", 60, 36, 0),
    ]},
    "scenario-alert": {"scripts": ("test-alert",), "extra_rules": "rifleman:\n\tHealth:\n\t\tHP: 3000\n", "actors": [
        ("rifleman", "Marines", 10, 10, 512),
        ("runner", "Xenos", 13, 10, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-hotkey-queue": {"scripts": ("test-hotkey-queue",), "actors": [
        ("cryo-pod", "Marines", 8, 8, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-repeat": _scenario("test-repeat", [
        ("cryo-pod", "Marines", 8, 8, 0),
    ]),
    # The only producer is destroyed mid-build with repeat on (see scenarios/test-producer-lost.lua).
    "scenario-producer-lost": {"scripts": ("test-producer-lost",), "drop_conquest": True, "actors": [
        ("cryo-pod", "Marines", 8, 8, 0), ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-repeat-broke": _scenario("test-repeat-broke", [
        ("cryo-pod", "Marines", 8, 8, 0),
    ]),
    "scenario-orbital-nojet": _scenario("test-orbital-nojet", [
        ("workshop", "Marines", 8, 8, 0),
        ("runner", "Xenos", 14, 10, 0),
    ]),
    "scenario-mend": {"scripts": ("test-mend",), "actors": [
        ("drone", "Xenos", 10, 10, 512),
        ("resin-turret", "Xenos", 10, 12, 512),
        ("rifleman", "Marines", 20, 20, 0),
    ]},
    "scenario-raid": {"scripts": ("wave-survival", "mission-raid", "test-raid"), "drop_conquest": True, "size": (40, 28), "ground": "landing_zone", "actors": HOLD_THE_LINE},
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
    # The lone rifleman only keeps the marines in the match: tough enough that the xenos' first squad cannot end it before they tech up.
    "scenario-ai-mix": {"scripts": ("test-ai-mix",), "xeno_bot": "skirmish", "size": (48, 48), "spawns": [(4, 4), (40, 40)],
                        "extra_rules": "rifleman:\n\tHealth:\n\t\tHP: 50000\n", "actors": [
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
    # A carrier lays a hugger egg off the weeds with its Lay Egg ability (see scenarios/test-egg-lay.lua).
    "scenario-egg-lay": {"scripts": ("test-egg-lay",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("carrier", "Xenos", 10, 10, 0), ("rifleman", "Marines", 14, 10, 512), ("cryo-pod", "Marines", 4, 18, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
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
    # The crusher must outlive the test: dead, it leaves an acid pool whose (enemy) burns would count as friends hurt.
    "scenario-nofriendlyfire": {"scripts": ("test-nofriendlyfire",), "extra_rules": "World:\n\tTgmcOptions:\n\t\tFriendlyFireDefault: false\ncrusher:\n\tHealth:\n\t\tHP: 20000\n", "actors": [
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
    # Not a test: the Upgrades tab with the Armory, Ordnance Depot and Workshop standing, to see what the player is offered.
    "shot-upgrades": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 160\n\t\tClickTick: 80\n\t\tClick: UPGRADE\n", "actors": [
        ("cryo-pod", "Marines", 6, 4, 0), ("engineer", "Marines", 8, 5, 256), ("armory", "Marines", 11, 7, 0), ("ordnance-depot", "Marines", 14, 7, 0), ("workshop", "Marines", 8, 7, 0), ("medbay", "Marines", 11, 11, 0),
        ("rifleman", "Marines", 10, 14, 512), ("hunter", "Xenos", 18, 12, 0), ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "shot-blast": {"scripts": ("shot-blast",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 156\n\t\tAlso: 159, 162, 166, 172, 180, 196, 232, 235, 238, 244, 256\n", "actors": [
        ("ordnance-depot", "Marines", 6, 6, 0), ("workshop", "Marines", 6, 9, 0),
        ("rifleman", "Marines", 12, 14, 512), ("hunter", "Xenos", 17, 12, 0), ("hunter", "Xenos", 14, 10, 0), ("resin-silo", "Xenos", 19, 19, 0),
    ]},
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
    # A crusher charges a marine, who is thrown away (see scenarios/test-knockback.lua).
    "scenario-knockback": {"scripts": ("test-knockback",), "size": (48, 24), "drop_conquest": True, "extra_rules": "rifleman:\n\tHealth:\n\t\tHP: 3000\ncrusher:\n\tArmament@PRIMARY:\n\t\tWeapon: TGMCCharge\n", "actors": [
        ("crusher", "Xenos", 10, 10, 0), ("rifleman", "Marines", 16, 10, 512), ("resin-silo", "Xenos", 40, 20, 0),
    ]},
    # The caste abilities (see scenarios/test-abilities.lua): a ravager, a praetorian facing a marine, a warrior beside one, a carrier.
    "scenario-abilities": {"scripts": ("test-abilities",), "size": (48, 32), "drop_conquest": True, "extra_rules": "rifleman:\n\tHealth:\n\t\tHP: 3000\n", "actors": [
        ("ravager", "Xenos", 6, 4, 0),
        ("praetorian", "Xenos", 10, 10, 768), ("rifleman", "Marines", 12, 10, 0),
        ("warrior", "Xenos", 10, 16, 256), ("rifleman", "Marines", 11, 16, 0),
        ("carrier", "Xenos", 30, 24, 768), ("rifleman", "Marines", 44, 28, 0),
        ("wraith", "Xenos", 6, 20, 256), ("rifleman", "Marines", 12, 20, 0), ("defiler", "Xenos", 20, 26, 768),
        ("resin-silo", "Xenos", 40, 4, 0),
    ]},
    # Not a test: marines being clawed, to see the blood on the floor (see Bleeds in tgmc/code/Blood.cs).
    "shot-bleed": {"scripts": ("shot-bleed",), "size": (32, 24), "drop_conquest": True, "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 150\nrifleman:\n\tHealth:\n\t\tHP: 3000\n", "actors": [
        ("rifleman", "Marines", 16, 12, 0), ("rifleman", "Marines", 17, 14, 0),
        ("crusher", "Xenos", 12, 12, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # Not a test: marines and a xeno killed by an explosion, to see the body parts and the blood (see ThrowsGibs in tgmc/code/Gibs.cs).
    "shot-gibs": {"scripts": ("shot-gibs",), "size": (32, 24), "drop_conquest": True, "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 70\n", "actors": [
        ("rifleman", "Marines", 14, 11, 0), ("rifleman", "Marines", 18, 13, 0), ("hunter", "Xenos", 16, 15, 0), ("resin-silo", "Xenos", 28, 20, 0),
        ("medic", "Marines", 16, 9, 0),
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
    # The command card with a squad leader selected (Not a test: a screenshot of the ability slots).
    # The card with frag autocast on (right-clicked) and the mouse over it: the AUTO line and the range circle.
    "shot-card-auto": {"scripts": ("shot-card-auto",), "size": (32, 24), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 80\n\t\tClickTick: 60\n\t\tSelect: rifleman\n\t\tRightClick: CMD_SLOT1\n\t\tHover: CMD_SLOT1\n", "actors": [
        ("rifleman", "Marines", 15, 12, 512),
        ("resin-silo", "Xenos", 28, 22, 0),
    ]},
    "shot-card": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 80\n\t\tSelect: squad_leader\n", "actors": [
        ("squad_leader", "Marines", 15, 12, 512),
        ("rifleman", "Marines", 16, 13, 512),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    # Veterancy on show (Not a test): riflemen at each rank with their stars, and the selected squad leader's rank line and bar.
    "shot-ranks": {"scripts": ("shot-ranks",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 60\n\t\tSelect: squad_leader\n", "actors": [
        ("squad_leader", "Marines", 15, 12, 512),
        ("rifleman", "Marines", 13, 13, 512), ("rifleman", "Marines", 15, 14, 512), ("rifleman", "Marines", 17, 13, 512),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    # A miner selected (Not a test): the card's income line.
    "shot-miner": {"scripts": ("shot-card-auto",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 60\n\t\tSelect: miner\n", "actors": [
        ("miner", "Marines", 15, 12, 0), ("rifleman", "Marines", 13, 13, 512),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    # The squad leader's MOVE! yell: the shout, the ring and the buff labels (Not a test).
    "shot-yell": {"scripts": ("shot-yell",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 72\n\t\tSelect: squad_leader\n", "actors": [
        ("squad_leader", "Marines", 15, 12, 512), ("rifleman", "Marines", 16, 13, 512), ("rifleman", "Marines", 14, 13, 512),
        ("rifleman", "Marines", 16, 11, 512), ("medic", "Marines", 13, 12, 512), ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    # A boiler's bombard and a bull's charge on a squad (Not a test).
    "shot-xeno-kits": {"scripts": ("shot-xeno-kits",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 74\n\t\tSelect: bull\n^Xeno:\n\tPlasma:\n\t\tStartPercent: 100\n", "actors": [
        ("boiler", "Xenos", 8, 10, 256), ("bull", "Xenos", 12, 8, 256), ("rifleman", "Marines", 16, 11, 768), ("rifleman", "Marines", 17, 12, 768),
        ("rifleman", "Marines", 16, 13, 768), ("cryo-pod", "Marines", 22, 22, 0), ("resin-silo", "Xenos", 3, 3, 0),
    ]},
    # A mixed selection, stepped once to the next unit type (Not a test).
    "shot-card-mixed": {"scripts": ("shot",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 80\n\t\tClickTick: 60\n\t\tSelect: squad_leader, rifleman, medic\n\t\tClick: CMD_NEXTTYPE\n", "actors": [
        ("squad_leader", "Marines", 15, 12, 512), ("rifleman", "Marines", 16, 13, 512), ("rifleman", "Marines", 14, 13, 512), ("medic", "Marines", 13, 12, 512),
        ("resin-silo", "Xenos", 22, 22, 0),
    ]},
    # The mech's walking dust, gun smoke and hit sparks (Not a test).
    # The ground effects in one view (see scenarios/shot-groundfx.lua): ash storm, bullet and acid holes, footprints, markers, heat bar.
    "shot-groundfx": {"scripts": ("shot-groundfx",), "size": (32, 24), "drop_conquest": True,
                      "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 150\n\tTgmcOptions:\n\t\tWeatherDefault: ash\nresin-turret:\n\tHealth:\n\t\tHP: 100000\ncade:\n\tHealth:\n\t\tHP: 100000\n", "actors": [
        ("resin-turret", "Xenos", 14, 6, 0), ("rifleman", "Marines", 8, 5, 256), ("rifleman", "Marines", 8, 7, 256), ("machinegunner", "Marines", 9, 6, 256),
        ("cade", "Marines", 12, 11, 0), ("spitter", "Xenos", 16, 11, 768),
        ("rifleman", "Marines", 12, 15, 768), ("rifleman", "Marines", 12, 17, 768), ("runner", "Xenos", 18, 19, 256),
        ("cryo-pod", "Marines", 3, 20, 0), ("workshop", "Marines", 3, 2, 0), ("resin-silo", "Xenos", 28, 22, 0),
    ]},
    # The castes added from TGMC side by side (see scenarios/shot-castes.lua).
    "shot-castes": {"scripts": ("shot-castes",), "size": (34, 20), "drop_conquest": True,
                    "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 40\nPlayer:\n\tShroud:\n\t\tFogCheckboxEnabled: false\n\t\tExploredMapCheckboxEnabled: true\npuppet:\n\t-Expires:\n", "actors": [
        ("nymph", "Xenos", 4, 6, 512), ("mantis", "Xenos", 8, 6, 512), ("baneling", "Xenos", 12, 6, 512), ("defender", "Xenos", 16, 6, 512), ("beetle", "Xenos", 20, 6, 512), ("gorger", "Xenos", 24, 6, 512), ("hivelord", "Xenos", 28, 6, 512), ("puppeteer", "Xenos", 4, 12, 512), ("puppet", "Xenos", 8, 12, 512), ("pyrogen", "Xenos", 12, 12, 512), ("scorpion", "Xenos", 16, 12, 512), ("dragon", "Xenos", 20, 12, 512), ("king", "Xenos", 24, 12, 512), ("cryo-pod", "Marines", 2, 18, 0), ("resin-silo", "Xenos", 30, 17, 0),
    ]},
    # The vehicles from TGMC side by side (see scenarios/shot-vehicles.lua).
    "shot-vehicles": {"scripts": ("shot-vehicles",), "size": (26, 20), "drop_conquest": True,
                      "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 30\n", "actors": [
        ("tank", "Marines", 6, 8, 256), ("apc", "Marines", 12, 8, 256), ("som-tank", "Marines", 18, 8, 768),
        ("tank", "Marines", 6, 13, 512), ("apc", "Marines", 12, 13, 512), ("som-tank", "Marines", 18, 13, 512),
        ("cryo-pod", "Marines", 2, 18, 0), ("resin-silo", "Xenos", 24, 2, 0),
    ]},
    "shot-mech-fx": {"scripts": ("shot-mech-fx",), "size": (32, 24), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 70\n", "actors": [
        ("mech", "Marines", 10, 12, 256), ("hunter", "Xenos", 17, 11, 768), ("hunter", "Xenos", 17, 13, 768), ("hunter", "Xenos", 18, 12, 768),
        ("cryo-pod", "Marines", 3, 3, 0), ("resin-silo", "Xenos", 28, 22, 0),
    ]},
    "shot-medic": {"scripts": ("shot-medic",), "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 160\n\t\tClickTick: 20\n\t\tSelect: rifleman\n\t\tClick: CMD_SLOT2\n", "actors": [
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
                       "size": (40, 28), "spawns": [(6, 14), (33, 13)], "ground": "landing_zone",
                       # Landing Zone's ore fields too (SKIRMISH_MAPS): without them neither bot has an income to speak of.
                       "actors": LANDING_ZONE + [("miner-field", "Neutral", x, y, 0) for x, y in ((11, 22), (28, 22), (12, 6), (27, 6), (21, 14))]
                       + [("platinum-vein", "Neutral", 21, 14, 0)]},
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
    # The marine bot's idle riflemen go and stand beside a miner far from its base, and stay (see scenarios/test-ai-guards.lua).
    "scenario-ai-guards": {"scripts": ("test-ai-guards",), "marine_bot": "easy", "drop_conquest": True, "size": (64, 32),
                           "extra_rules": "^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": [
        ("cryo-pod", "Marines", 6, 6, 0), ("rifleman", "Marines", 9, 8, 0), ("rifleman", "Marines", 10, 8, 0),
        ("rifleman", "Marines", 9, 9, 0), ("rifleman", "Marines", 10, 9, 0), ("rifleman", "Marines", 11, 9, 0),
        ("miner-field", "Neutral", 40, 20, 0), ("miner", "Marines", 40, 20, 0), ("resin-silo", "Xenos", 58, 28, 0),
    ]},
    # ThreatMemory: what the marines saw of three xenos is remembered, then fades (see scenarios/test-ai-threat.lua).
    "scenario-ai-threat": {"scripts": ("test-ai-threat",), "drop_conquest": True, "size": (64, 48),
                           "extra_rules": "^Unit:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": [
        ("cryo-pod", "Marines", 6, 6, 0), ("rifleman", "Marines", 8, 8, 0),
        ("sentinel", "Xenos", 30, 24, 0), ("sentinel", "Xenos", 31, 24, 0), ("sentinel", "Xenos", 30, 25, 0),
        ("resin-silo", "Xenos", 58, 42, 0),
    ]},
    # Bot personality rusher (see scenarios/test-ai-personality.lua): eight riflemen at home, no money.
    "scenario-ai-rusher": {"scripts": ("test-ai-personality", "personality-case-rusher"), "marine_bot": "rusher", "extra_rules": "Player:\n\tPlayerResources:\n\t\tDefaultCash: 0\n\tShroud:\n\t\tFogCheckboxEnabled: false\n\t\tExploredMapCheckboxEnabled: true\n", "drop_conquest": True, "size": (64, 40), "actors": [
        ("cryo-pod", "Marines", 6, 20, 0), ("resin-silo", "Xenos", 60, 36, 0), ("rifleman", "Marines", 8, 18, 0), ("rifleman", "Marines", 9, 18, 0), ("rifleman", "Marines", 10, 18, 0), ("rifleman", "Marines", 8, 19, 0), ("rifleman", "Marines", 9, 19, 0), ("rifleman", "Marines", 10, 19, 0), ("rifleman", "Marines", 8, 17, 0), ("rifleman", "Marines", 9, 17, 0),
    ]},
    # Bot personality turtle (see scenarios/test-ai-personality.lua): eight riflemen at home, no money.
    "scenario-ai-turtle": {"scripts": ("test-ai-personality", "personality-case-turtle"), "marine_bot": "turtle", "extra_rules": "Player:\n\tPlayerResources:\n\t\tDefaultCash: 0\n\tShroud:\n\t\tFogCheckboxEnabled: false\n\t\tExploredMapCheckboxEnabled: true\n", "drop_conquest": True, "size": (64, 40), "actors": [
        ("cryo-pod", "Marines", 6, 20, 0), ("resin-silo", "Xenos", 60, 36, 0), ("rifleman", "Marines", 8, 18, 0), ("rifleman", "Marines", 9, 18, 0), ("rifleman", "Marines", 10, 18, 0), ("rifleman", "Marines", 8, 19, 0), ("rifleman", "Marines", 9, 19, 0), ("rifleman", "Marines", 10, 19, 0), ("rifleman", "Marines", 8, 17, 0), ("rifleman", "Marines", 9, 17, 0),
    ]},
    # DefendBotModule: xenos hit a marine sentry (on HoldFire) far from the base; the bot sends riflemen, enough but not all (see scenarios/test-ai-defend.lua).
    "scenario-ai-defend": {"scripts": ("test-ai-defend", "defend-case-help"), "marine_bot": "easy", "extra_rules": "Player:\n\t-ScoutBotModule@marines:\n\t-FieldBotModule@sweep:\n", "drop_conquest": True, "size": (64, 40), "actors": [
        ("cryo-pod", "Marines", 6, 20, 0), ("sentry-turret", "Marines", 40, 20, 0), ("resin-silo", "Xenos", 60, 36, 0), ("rifleman", "Marines", 8, 18, 0), ("rifleman", "Marines", 9, 18, 0), ("rifleman", "Marines", 10, 18, 0),
        ("rifleman", "Marines", 8, 19, 0), ("rifleman", "Marines", 9, 19, 0), ("rifleman", "Marines", 10, 19, 0), ("rifleman", "Marines", 8, 17, 0), ("rifleman", "Marines", 9, 17, 0),
    ]},
    # The same, but the victim is a sentry that dies at once: the riflemen are handed back and nothing breaks.
    "scenario-ai-defend-victim-dies": {"scripts": ("test-ai-defend", "defend-case-dies"), "marine_bot": "easy", "extra_rules": "Player:\n\t-ScoutBotModule@marines:\n\t-FieldBotModule@sweep:\n", "drop_conquest": True, "size": (64, 40), "actors": [
        ("cryo-pod", "Marines", 6, 20, 0), ("sentry-turret", "Marines", 40, 20, 0), ("resin-silo", "Xenos", 60, 36, 0), ("rifleman", "Marines", 8, 18, 0), ("rifleman", "Marines", 9, 18, 0), ("rifleman", "Marines", 10, 18, 0),
        ("rifleman", "Marines", 8, 19, 0), ("rifleman", "Marines", 9, 19, 0), ("rifleman", "Marines", 10, 19, 0), ("rifleman", "Marines", 8, 17, 0), ("rifleman", "Marines", 9, 17, 0),
    ]},
    # The same with no riflemen at all: nothing to send, nothing breaks.
    "scenario-ai-defend-nobody": {"scripts": ("test-ai-defend", "defend-case-nobody"), "marine_bot": "easy", "extra_rules": "Player:\n\t-ScoutBotModule@marines:\n\t-FieldBotModule@sweep:\n", "drop_conquest": True, "size": (64, 40), "actors": [
        ("cryo-pod", "Marines", 6, 20, 0), ("sentry-turret", "Marines", 40, 20, 0), ("resin-silo", "Xenos", 60, 36, 0),
    ]},
    # RaidBotModule, a bare miner and one with three sentries, equally far: the raid goes for the bare one (see scenarios/test-ai-raid.lua).
    "scenario-ai-raid": {"scripts": ("test-ai-raid", "raid-case-pick"), "xeno_bot": "easy", "drop_conquest": True, "size": (64, 40),
        "extra_rules": "Player:\n\t-ScoutBotModule@xenos:\n\t-FieldBotModule@xenos:\n\tThreatMemory:\n\t\tFullVision: true\n", "actors": [
        ("cryo-pod", "Marines", 4, 20, 0), ("resin-silo", "Xenos", 58, 20, 0), ("runner", "Xenos", 54, 19, 0), ("runner", "Xenos", 54, 21, 0), ("runner", "Xenos", 55, 19, 0), ("runner", "Xenos", 55, 21, 0), ("runner", "Xenos", 56, 19, 0), ("runner", "Xenos", 56, 21, 0),
        ("miner", "Marines", 30, 6, 0), ("miner", "Marines", 30, 34, 0),
        ("sentry-turret", "Marines", 28, 33, 0), ("sentry-turret", "Marines", 32, 33, 0), ("sentry-turret", "Marines", 30, 31, 0),

    ]},
    # RaidBotModule, sentries appear beside the target as the raid nears: it turns home (see scenarios/test-ai-raid.lua).
    "scenario-ai-raid-backoff": {"scripts": ("test-ai-raid", "raid-case-backoff"), "xeno_bot": "easy", "drop_conquest": True, "size": (64, 40),
        "extra_rules": "Player:\n\t-ScoutBotModule@xenos:\n\t-FieldBotModule@xenos:\n\tThreatMemory:\n\t\tFullVision: true\n", "actors": [
        ("cryo-pod", "Marines", 4, 20, 0), ("resin-silo", "Xenos", 58, 20, 0), ("runner", "Xenos", 54, 19, 0), ("runner", "Xenos", 54, 21, 0), ("runner", "Xenos", 55, 19, 0), ("runner", "Xenos", 55, 21, 0), ("runner", "Xenos", 56, 19, 0), ("runner", "Xenos", 56, 21, 0),
        ("miner", "Marines", 30, 6, 0),
    ]},
    # RaidBotModule, a sentry wall on the straight line to the target: the raid walks round it (see scenarios/test-ai-raid.lua).
    "scenario-ai-raid-rich": {"scripts": ("test-ai-raid", "raid-case-rich"), "xeno_bot": "easy", "drop_conquest": True, "size": (64, 40),
        "extra_rules": "Player:\n\t-ScoutBotModule@xenos:\n\t-FieldBotModule@xenos:\n\tThreatMemory:\n\t\tFullVision: true\nminer:\n\tValued:\n\t\tCost: 400\n", "actors": [
        ("cryo-pod", "Marines", 4, 20, 0), ("resin-silo", "Xenos", 58, 20, 0), ("runner", "Xenos", 54, 19, 0), ("runner", "Xenos", 54, 21, 0), ("runner", "Xenos", 55, 19, 0), ("runner", "Xenos", 55, 21, 0), ("runner", "Xenos", 56, 19, 0), ("runner", "Xenos", 56, 21, 0),
        ("miner", "Marines", 30, 6, 0),
    ]},
    "scenario-ai-raid-route": {"scripts": ("test-ai-raid", "raid-case-route"), "xeno_bot": "easy", "drop_conquest": True, "size": (64, 40),
        "extra_rules": "Player:\n\t-ScoutBotModule@xenos:\n\t-FieldBotModule@xenos:\n\tThreatMemory:\n\t\tFullVision: true\n", "actors": [
        ("cryo-pod", "Marines", 4, 20, 0), ("resin-silo", "Xenos", 58, 20, 0), ("runner", "Xenos", 54, 19, 0), ("runner", "Xenos", 54, 21, 0), ("runner", "Xenos", 55, 19, 0), ("runner", "Xenos", 55, 21, 0), ("runner", "Xenos", 56, 19, 0), ("runner", "Xenos", 56, 21, 0),
        ("miner", "Marines", 20, 20, 0),
        ("sentry-turret", "Marines", 40, 16, 0), ("sentry-turret", "Marines", 40, 18, 0), ("sentry-turret", "Marines", 40, 20, 0),
        ("sentry-turret", "Marines", 40, 22, 0), ("sentry-turret", "Marines", 40, 24, 0),
    ]},
    # AttackTargetBotModule: the squad goes for the bare mini-silo B, not the nearer C behind turrets it cannot beat, and not A (one turret)
    # (see scenarios/test-ai-attack-weak.lua).
    "scenario-ai-attack-weak": {"scripts": ("test-ai-attack-weak",), "marine_bot": "hard", "drop_conquest": True, "size": (64, 40),
        "extra_rules": "Player:\n\t-ScoutBotModule@marines:\n\t-FieldBotModule@sweep:\n\t-RaidBotModule@marines:\n\t-TgmcSupportPowerBotModule:\n\tThreatMemory:\n\t\tFullVision: true\n", "actors": [
        ("cryo-pod", "Marines", 4, 20, 0), ("rifleman", "Marines", 6, 19, 0), ("rifleman", "Marines", 6, 21, 0), ("rifleman", "Marines", 7, 19, 0), ("rifleman", "Marines", 7, 21, 0), ("rifleman", "Marines", 8, 19, 0), ("rifleman", "Marines", 8, 21, 0), ("rifleman", "Marines", 9, 19, 0), ("rifleman", "Marines", 9, 21, 0),
        ("mini-silo", "Xenos", 44, 6, 0), ("resin-turret", "Xenos", 46, 8, 0),
        ("mini-silo", "Xenos", 44, 34, 0),
        ("mini-silo", "Xenos", 28, 4, 0), ("resin-turret", "Xenos", 26, 6, 0), ("resin-turret", "Xenos", 30, 6, 0),
        ("resin-silo", "Xenos", 60, 20, 0), ("resin-turret", "Xenos", 58, 18, 0), ("resin-turret", "Xenos", 58, 22, 0), ("resin-turret", "Xenos", 61, 23, 0),
    ]},
    # Two riflemen, both miner guards, with the hard bot's scout on: the scout must not take a guard (see scenarios/test-ai-guards.lua).
    "scenario-ai-guards-busy": {"scripts": ("test-ai-guards",), "marine_bot": "hard", "drop_conquest": True, "size": (64, 32),
                           "extra_rules": "^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": [
        ("cryo-pod", "Marines", 6, 6, 0), ("rifleman", "Marines", 9, 8, 0), ("rifleman", "Marines", 10, 8, 0),
        ("miner-field", "Neutral", 40, 20, 0), ("miner", "Marines", 40, 20, 0), ("resin-silo", "Xenos", 58, 28, 0),
    ]},
    # Marine riflemen shoot a xeno mini-silo from rifle range, beyond DefendBotModule's Radius: the xenos still answer (see scenarios/test-ai-defend-ranged.lua).
    "scenario-ai-defend-ranged": {"scripts": ("test-ai-defend-ranged",), "xeno_bot": "easy", "drop_conquest": True, "size": (64, 40),
        "extra_rules": "Player:\n\t-ScoutBotModule@xenos:\n\t-FieldBotModule@xenos:\n", "actors": [
        ("cryo-pod", "Marines", 4, 36, 0), ("resin-silo", "Xenos", 58, 20, 0), ("runner", "Xenos", 54, 19, 0), ("runner", "Xenos", 54, 21, 0), ("runner", "Xenos", 55, 19, 0), ("runner", "Xenos", 55, 21, 0), ("runner", "Xenos", 56, 19, 0), ("runner", "Xenos", 56, 21, 0), ("runner", "Xenos", 57, 19, 0), ("runner", "Xenos", 57, 21, 0),
        ("mini-silo", "Xenos", 24, 20, 0),
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
                             "extra_rules": "Player:\n\t-SquadManagerBotModule@xenos-easy:\n\t-SquadManagerBotModule@xenos-normal:\n\t-SquadManagerBotModule@xenos-hard:\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\nevolution-tower:\n\tGrantExternalConditionPower@cure:\n\t\tChargeInterval: 60\n\tCallOfTheBurrowedPower@burrowed:\n\t\tChargeInterval: 60\nrifleman:\n\tHealth:\n\t\tHP: 5000\n", "actors": [
        ("evolution-tower", "Xenos", 6, 6, 0), ("maturity-tower", "Xenos", 10, 6, 0),
        ("hunter", "Xenos", 24, 20, 0), ("hunter", "Xenos", 25, 21, 0), ("hunter", "Xenos", 24, 22, 0), ("hunter", "Xenos", 26, 20, 0), ("hunter", "Xenos", 26, 22, 0),
        ("rifleman", "Marines", 30, 22, 512), ("rifleman", "Marines", 31, 24, 512),
        ("resin-silo", "Xenos", 3, 3, 0),
    ]},
    # The xeno AI creeps its weeds out with drones (see scenarios/test-ai-weeds.lua): no squads, a silo and two drones, plenty of cash.
    "scenario-ai-weeds": {"scripts": ("test-ai-weeds",), "xeno_bot": "skirmish", "fast": True, "drop_conquest": True, "size": (72, 40),
                          "extra_rules": "Player:\n\t-SquadManagerBotModule@xenos-easy:\n\t-SquadManagerBotModule@xenos-normal:\n\t-SquadManagerBotModule@xenos-hard:\n", "actors": [
        ("resin-silo", "Xenos", 12, 20, 0), ("drone", "Xenos", 14, 22, 0), ("drone", "Xenos", 14, 18, 0),
        ("rifleman", "Marines", 64, 20, 512),
    ]},
    # The xeno AI builds its own drone and sends it out (see scenarios/test-ai-drone-build.lua): no drones at the start.
    "scenario-ai-drone-build": {"scripts": ("test-ai-drone-build",), "xeno_bot": "skirmish", "fast": True, "drop_conquest": True, "size": (72, 40),
                                "extra_rules": "Player:\n\t-SquadManagerBotModule@xenos-easy:\n\t-SquadManagerBotModule@xenos-normal:\n\t-SquadManagerBotModule@xenos-hard:\n", "actors": [
        ("resin-silo", "Xenos", 12, 20, 0), ("rifleman", "Marines", 64, 20, 512),
    ]},
    # The workshop's mech drop (see scenarios/test-mechdrop.lua).
    "scenario-mechdrop": {"scripts": ("test-mechdrop",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("workshop", "Marines", 6, 6, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # The xeno AI uses a caste ability by itself (see scenarios/test-ai-abilities.lua): a crusher that holds fire, with marines close by.
    "scenario-ai-abilities": {"scripts": ("test-ai-abilities",), "xeno_bot": "skirmish", "drop_conquest": True, "size": (40, 24),
                              "extra_rules": "Player:\n\t-SquadManagerBotModule@xenos-easy:\n\t-SquadManagerBotModule@xenos-normal:\n\t-SquadManagerBotModule@xenos-hard:\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\ncrusher:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\nrifleman:\n\tHealth:\n\t\tHP: 3000\n", "actors": [
        ("crusher", "Xenos", 14, 12, 0), ("rifleman", "Marines", 16, 12, 512), ("rifleman", "Marines", 16, 13, 512), ("rifleman", "Marines", 15, 14, 512),
        ("resin-silo", "Xenos", 30, 20, 0),
    ]},
    # The marine AI calls a drop pod by itself (see scenarios/test-ai-pod.lua): squads removed, units hold fire, the pod ready at once.
    "scenario-ai-pod": {"scripts": ("test-ai-pod",), "marine_bot": "skirmish", "drop_conquest": True, "size": (48, 32),
                        "extra_rules": "Player:\n\t-SquadManagerBotModule@marines-easy:\n\t-SquadManagerBotModule@marines-normal:\n\t-SquadManagerBotModule@marines-hard:\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\ncryo-pod:\n\tDropPodPower@droppod:\n\t\tChargeInterval: 60\n", "actors": [
        # The rifleman watches the hunters from 7 cells: close enough to see them, outside the 6 cells in which the AI's pod
        # counts its own infantry against the spot.
        ("cryo-pod", "Marines", 6, 6, 0), ("rifleman", "Marines", 15, 22, 512),
        ("hunter", "Xenos", 22, 22, 0), ("hunter", "Xenos", 23, 23, 0), ("hunter", "Xenos", 22, 24, 0), ("hunter", "Xenos", 23, 22, 0),
        ("hunter", "Xenos", 21, 23, 0), ("resin-silo", "Xenos", 44, 28, 0),
    ]},
    # Plasma pays for abilities (see scenarios/test-plasma.lua): a ravager that starts nearly empty.
    "scenario-plasma": {"scripts": ("test-plasma",), "size": (32, 24), "drop_conquest": True, "extra_rules": "ravager:\n\tPlasma:\n\t\tStartPercent: 10\n", "actors": [
        ("ravager", "Xenos", 8, 10, 0), ("resin-silo", "Xenos", 28, 20, 0), ("rifleman", "Marines", 4, 4, 0), ("sentinel", "Xenos", 26, 4, 0),
    ]},
    # Xenos mend and gain plasma faster on weeds (see scenarios/test-weed-heal.lua): the runner at x 8 stands on weeds.
    "scenario-weed-heal": {"scripts": ("test-weed-heal",), "size": (32, 24), "drop_conquest": True, "extra_rules": "runner:\n\tPlasma:\n\t\tStartPercent: 10\n", "actors": [
        ("weeds", "Xenos", 8, 10, 0), ("runner", "Xenos", 8, 10, 0), ("runner", "Xenos", 20, 10, 0), ("resin-silo", "Xenos", 28, 20, 0), ("rifleman", "Marines", 4, 4, 0),
    ]},
    # Resin doors open for the hive only, and sticky resin slows marines (see scenarios/test-resin-door.lua). Two walled lanes with a
    # door at x 11 (the xenos' lane at y 10, the marines' at y 14, each closed off above and below), a strip of sticky resin at y 19.
    "scenario-resin-door": {"scripts": ("test-resin-door",), "size": (32, 28), "drop_conquest": True, "actors": [
        ("resin-wall", "Xenos", 9, 9, 0), ("resin-wall", "Xenos", 9, 11, 0), ("resin-wall", "Xenos", 10, 9, 0), ("resin-wall", "Xenos", 10, 11, 0), ("resin-wall", "Xenos", 11, 9, 0), ("resin-wall", "Xenos", 11, 11, 0), ("resin-wall", "Xenos", 12, 9, 0), ("resin-wall", "Xenos", 12, 11, 0), ("resin-wall", "Xenos", 13, 9, 0), ("resin-wall", "Xenos", 13, 11, 0), ("resin-wall", "Xenos", 11, 8, 0), ("resin-wall", "Xenos", 11, 12, 0), 
        ("resin-wall", "Xenos", 9, 13, 0), ("resin-wall", "Xenos", 9, 15, 0), ("resin-wall", "Xenos", 10, 13, 0), ("resin-wall", "Xenos", 10, 15, 0), ("resin-wall", "Xenos", 11, 13, 0), ("resin-wall", "Xenos", 11, 15, 0), ("resin-wall", "Xenos", 12, 13, 0), ("resin-wall", "Xenos", 12, 15, 0), ("resin-wall", "Xenos", 13, 13, 0), ("resin-wall", "Xenos", 13, 15, 0), ("resin-wall", "Xenos", 11, 12, 0), ("resin-wall", "Xenos", 11, 16, 0), 
        ("resin-door", "Xenos", 11, 10, 0), ("resin-door", "Xenos", 11, 14, 0),
        ("sticky-resin", "Xenos", 7, 19, 0), ("sticky-resin", "Xenos", 8, 19, 0), ("sticky-resin", "Xenos", 9, 19, 0), ("sticky-resin", "Xenos", 10, 19, 0), ("sticky-resin", "Xenos", 11, 19, 0), ("sticky-resin", "Xenos", 12, 19, 0), ("sticky-resin", "Xenos", 13, 19, 0), ("sticky-resin", "Xenos", 14, 19, 0), 
        ("runner", "Xenos", 5, 10, 0), ("rifleman", "Marines", 5, 14, 0), ("rifleman", "Marines", 5, 19, 0), ("rifleman", "Marines", 5, 22, 0),
        ("resin-silo", "Xenos", 28, 3, 0),
    ]},
    # A wall stops rifle bullets (see scenarios/test-cover.lua): the wall of the walls ground at x 14 to 16, y 8 to 15.
    "scenario-cover": {"scripts": ("test-cover",), "size": (32, 24), "drop_conquest": True, "ground": "walls",
                       "extra_rules": "hunter:\n\tHealth:\n\t\tHP: 3000\n", "actors": [
        ("rifleman", "Marines", 12, 12, 256), ("hunter", "Xenos", 17, 12, 0),
        ("rifleman", "Marines", 12, 4, 256), ("hunter", "Xenos", 17, 4, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # Melee xenos claw down marine structures (see scenarios/test-xeno-structures.lua): a hunter and a runner against a cade, then a sentry.
    "scenario-xeno-structures": {"scripts": ("test-xeno-structures",), "size": (32, 24), "drop_conquest": True,
                                 "extra_rules": "hunter:\n\tHealth:\n\t\tHP: 3000\nrunner:\n\tHealth:\n\t\tHP: 3000\n", "actors": [
        ("cade", "Marines", 10, 4, 0), ("hunter", "Xenos", 14, 4, 768), ("cade", "Marines", 10, 8, 0), ("runner", "Xenos", 14, 8, 768),
        ("sentry-turret", "Marines", 10, 12, 0), ("hunter", "Xenos", 14, 12, 768), ("sentry-turret", "Marines", 10, 16, 0), ("runner", "Xenos", 14, 16, 768),
        ("cryo-pod", "Marines", 3, 20, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # A barricade covers only the side it faces (see scenarios/test-cade.lua): one faces the rifleman in the north, one faces the hunter in the south.
    "scenario-cade": {"scripts": ("test-cade",), "size": (32, 24), "drop_conquest": True,
                      "extra_rules": "hunter:\n\tHealth:\n\t\tHP: 3000\ncade-w:\n\tInherits: ^MapObjectCover\n\tHealth:\n\t\tHP: 3000\n\tWithSpriteBody:\n\t\tSequence: o0\n\tBlocksBullets:\n\t\tFaceX: -1\n\t\tFaceY: 0\ncade-e:\n\tInherits: cade-w\n\tBlocksBullets:\n\t\tFaceX: 1\n\t\tFaceY: 0\n", "actors": [
        ("rifleman", "Marines", 12, 4, 256), ("cade-w", "Neutral", 14, 4, 0), ("hunter", "Xenos", 17, 4, 0),
        ("rifleman", "Marines", 12, 12, 256), ("cade-e", "Neutral", 14, 12, 0), ("hunter", "Xenos", 17, 12, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # The orbital strike (see scenarios/test-orbital.lua): hunters and a wall at the target.
    "scenario-orbital": {"scripts": ("test-orbital",), "drop_conquest": True, "size": (32, 24), "ground": "walls", "actors": [
        ("workshop", "Marines", 6, 6, 0), ("hunter", "Xenos", 12, 11, 0), ("hunter", "Xenos", 18, 12, 0), ("hunter", "Xenos", 15, 9, 0),
        ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # The rail gun, the cluster warhead and the incendiary warhead (see scenarios/test-orbital-kinds.lua).
    "scenario-orbital-kinds": {"scripts": ("test-orbital-kinds",), "drop_conquest": True, "size": (32, 24), "ground": "walls", "actors": [
        ("workshop", "Marines", 6, 6, 0), ("hunter", "Xenos", 12, 11, 0), ("hunter", "Xenos", 13, 11, 0), ("hunter", "Xenos", 12, 12, 0), ("hunter", "Xenos", 11, 11, 0),
        ("hunter", "Xenos", 24, 12, 0), ("hunter", "Xenos", 25, 12, 0), ("hunter", "Xenos", 23, 13, 0), ("hunter", "Xenos", 24, 11, 0),
        ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # Pods carrying a mortar and a sentry on awkward spots (see scenarios/test-podcarry.lua).
    "scenario-podcarry": {"scripts": ("test-podcarry",), "drop_conquest": True, "size": (32, 24), "ground": "walls", "actors": [
        ("cryo-pod", "Marines", 6, 6, 0), ("rifleman", "Marines", 10, 12, 0), ("rifleman", "Marines", 20, 12, 0),
        ("hunter", "Xenos", 17, 10, 0), ("hunter", "Xenos", 17, 13, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # A SOM player's drop pod lands SOM troops, not marines (see scenarios/test-som-pod.lua).
    "scenario-som-pod": {"scripts": ("test-som-pod",), "drop_conquest": True, "size": (32, 24), "human_faction": "som", "actors": [
        ("cryo-pod", "Marines", 6, 6, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # A unit walks through a door in a wall (see scenarios/test-door.lua): mapdoor-0 is any generated door.
    "scenario-door": {"scripts": ("test-door",), "drop_conquest": True, "size": (32, 24), "ground": "doorline", "actors": [
        ("rifleman", "Marines", 10, 11, 0), ("mapdoor-0", "Neutral", 14, 11, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # Not a test: a door opening for a marine, to see the animation.
    # The Alamo down on the Evac landing zone, doors open, marines on the way (see scenarios/shot-evac.lua).
    "shot-evac": {"scripts": ("mission-evac", "shot-evac"), "drop_conquest": True, "size": (64, 48), "ground": "evac",
                  "extra_rules": EVAC_RULES + "World:\n\tScreenshotAt:\n\t\tTick: 260\n", "actors": EVAC},
    # The Alamo partway down as it flies in, its shadow on the landing zone (see Dropship in tgmc/code/Dropship.cs).
    "shot-evac-flyin": {"scripts": ("mission-evac", "shot-evac"), "drop_conquest": True, "size": (64, 48), "ground": "evac",
                        "extra_rules": EVAC_RULES + "World:\n\tScreenshotAt:\n\t\tTick: 80\n", "actors": EVAC},
    "shot-door": {"scripts": ("shot-door",), "drop_conquest": True, "size": (32, 24), "ground": "doorline", "extra_rules": "World:\n\tScreenshotAt:\n\t\tTick: 75\n", "actors": [
        ("rifleman", "Marines", 12, 11, 0), ("mapdoor-0", "Neutral", 14, 11, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # The suicide vest (see scenarios/test-bomber.lua): a bomber detonates next to two hunters.
    "scenario-bomber": {"scripts": ("test-bomber",), "drop_conquest": True, "size": (32, 24), "extra_rules": "hunter:\n\tHealth:\n\t\tHP: 3000\n", "actors": [
        ("bomber", "Marines", 10, 10, 0), ("hunter", "Xenos", 12, 10, 0), ("hunter", "Xenos", 12, 11, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # Not a test: the lobby's Night option. Dark ground, flashlights that walk with the marines, base lamps, mech headlights, flamer fire,
    # gunfire flashes and the resin silo's purple glow (see NightLighting in tgmc/code/Lights.cs).
    "shot-lighting": {"scripts": ("shot-card-auto",), "drop_conquest": True, "size": (32, 24),
                      "extra_rules": "World:\n\tTgmcOptions:\n\t\tNightDefault: true\n\tScreenshotAt:\n\t\tTick: 110\n", "actors": [
        ("rifleman", "Marines", 15, 12, 256), ("flamer", "Marines", 14, 13, 256), ("armory", "Marines", 8, 8, 0), ("mech", "Marines", 10, 15, 256),
        ("runner", "Xenos", 20, 12, 768), ("runner", "Xenos", 20, 13, 768), ("resin-silo", "Xenos", 21, 7, 0),
    ]},
    # The squad leader's Mirage decoy and Mark (see scenarios/test-squadgear.lua).
    "scenario-squadgear": {"scripts": ("test-squadgear",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("squad_leader", "Marines", 10, 10, 256), ("hunter", "Xenos", 16, 10, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # The workshop builds a mech (see scenarios/test-mechbuild.lua).
    "scenario-mechbuild": {"scripts": ("test-mechbuild",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("workshop", "Marines", 8, 8, 0), ("armory", "Marines", 12, 8, 0), ("vendor", "Marines", 16, 8, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # The marine AI uses its support powers (see scenarios/test-ai-support.lua).
    "scenario-ai-support": {"scripts": ("test-ai-support",), "marine_bot": "skirmish", "drop_conquest": True, "size": (48, 32),
                            "extra_rules": "Player:\n\t-SquadManagerBotModule@marines-easy:\n\t-SquadManagerBotModule@marines-normal:\n\t-SquadManagerBotModule@marines-hard:\n^Infantry:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\ncryo-pod:\n\tDropPodPower@sentrydrop:\n\t\tChargeInterval: 60\n\tDropPodPower@mortardrop:\n\t\tChargeInterval: 60\narmory:\n\tDropPodPower@supplydrop:\n\t\tChargeInterval: 60\n\tTgmcSpawnActorPower@smoke:\n\t\tChargeInterval: 60\n", "actors": [
        ("cryo-pod", "Marines", 6, 6, 0), ("armory", "Marines", 10, 6, 0), ("rifleman", "Marines", 17, 22, 512),
        ("rifleman", "Marines", 17, 23, 512), ("rifleman", "Marines", 17, 24, 512), ("medic", "Marines", 16, 23, 512),
        ("hunter", "Xenos", 22, 22, 0), ("hunter", "Xenos", 23, 23, 0), ("hunter", "Xenos", 22, 24, 0), ("hunter", "Xenos", 23, 21, 0),
        ("hunter", "Xenos", 23, 25, 0), ("hunter", "Xenos", 22, 23, 0), ("resin-silo", "Xenos", 44, 28, 0),
    ]},
    # Gunfire and acid damage the objects of the converted maps (see scenarios/test-objects-damage.lua): mapobj-0 is any generated map object.
    # The xeno AI sends its idle attackers to the unclaimed ore fields (FieldBotModule in tgmc/code/Bots/; see scenarios/test-ai-fields.lua).
    "scenario-ai-fields": {"scripts": ("test-ai-fields",), "xeno_bot": "hard", "drop_conquest": True, "fast": True, "size": (64, 40), "spawns": [(4, 4), (60, 36)], "actors": [
        ("resin-silo", "Xenos", 8, 8, 0), ("miner-field", "Neutral", 14, 9, 0), ("miner-field", "Neutral", 50, 30, 0),
    ]},
    # Marine AI and xeno AI play: marines should claim fields, xenos disable them (see scenarios/test-ai-marine-fields.lua).
    "scenario-ai-marine-fields": {"scripts": ("test-ai-marine-fields",), "marine_bot": "hard", "xeno_bot": "hard", "fast": True, "size": (64, 40), "spawns": [(4, 30), (58, 8)], "actors": [
        ("cryo-pod", "Marines", 4, 30, 0), ("resin-silo", "Xenos", 58, 8, 0),
        ("miner-field", "Neutral", 12, 28, 0), ("miner-field", "Neutral", 30, 18, 0), ("miner-field", "Neutral", 52, 10, 0),
    ]},
    # The same match at the easy bot level (see scenarios/test-ai-marine-fields.lua).
    "scenario-ai-marine-fields-easy": {"scripts": ("test-ai-marine-fields",), "marine_bot": "easy", "xeno_bot": "easy", "fast": True, "size": (64, 40), "spawns": [(4, 30), (58, 8)], "actors": [
        ("cryo-pod", "Marines", 4, 30, 0), ("resin-silo", "Xenos", 58, 8, 0),
        ("miner-field", "Neutral", 12, 28, 0), ("miner-field", "Neutral", 30, 18, 0), ("miner-field", "Neutral", 52, 10, 0),
    ]},
    # An idle engineer beside a broken ore field, with no order: does it repair the field by itself? (see scenarios/test-engineer-autorepair.lua)
    # An engineer beside a damaged cade shoots the xeno in reach before it welds (see scenarios/test-engineer-shoots.lua).
    "scenario-engineer-shoots": {"scripts": ("test-engineer-shoots",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("engineer", "Marines", 8, 10, 256), ("cade", "Marines", 9, 11, 0), ("runner", "Xenos", 11, 10, 768), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    "scenario-card-slots": {"scripts": ("test-card-slots",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("squad_leader", "Marines", 10, 10, 256), ("runner", "Xenos", 16, 10, 768), ("cryo-pod", "Marines", 4, 18, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    "scenario-card-mixed": {"scripts": ("test-card-mixed",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("squad_leader", "Marines", 10, 10, 256), ("rifleman", "Marines", 11, 10, 256), ("rifleman", "Marines", 10, 11, 256),
        ("rifleman", "Marines", 11, 11, 256), ("cryo-pod", "Marines", 4, 18, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    "scenario-ability-aim": {"scripts": ("test-ability-aim",), "drop_conquest": True, "size": (32, 24), "extra_rules": "rifleman:\n\tActiveAbility@testaim:\n\t\tOrderName: AbilityTestAim\n\t\tSlot: 7\n\t\tLabel: Grenade\n\t\tAim: Target\n\t\tRange: 5c0\n\t\tCooldown: 50\n\t\tWeapon: TGMCGrenade\n\tActiveAbility@testaimactor:\n\t\tOrderName: AbilityTestAimActor\n\t\tSlot: 8\n\t\tLabel: Throw\n\t\tAim: TargetActor\n\t\tRange: 5c0\n\t\tCooldown: 50\n\t\tWeapon: TGMCGrenade\n", "actors": [
        ("rifleman", "Marines", 6, 10, 256), ("runner", "Xenos", 10, 10, 768), ("runner", "Xenos", 18, 10, 768), ("runner", "Xenos", 8, 21, 0),
        ("cryo-pod", "Marines", 2, 2, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    "scenario-ability-toggle": {"scripts": ("test-ability-toggle",), "drop_conquest": True, "size": (32, 24), "extra_rules": "mortarman:\n\tArmament@PRIMARY:\n\t\tRequiresCondition: shell-he\n\tArmament@SMOKE:\n\t\tWeapon: TGMCSmokeScreen\n\t\tRequiresCondition: shell-smoke\n\tActiveAbility@he:\n\t\tOrderName: AbilityShellHE\n\t\tSlot: 1\n\t\tLabel: HE\n\t\tToggle: true\n\t\tGroup: shell\n\t\tStartOn: true\n\t\tCondition: shell-he\n\t\tCooldown: 0\n\tActiveAbility@smoke:\n\t\tOrderName: AbilityShellSmoke\n\t\tSlot: 2\n\t\tLabel: Smoke\n\t\tToggle: true\n\t\tGroup: shell\n\t\tCondition: shell-smoke\n\t\tCooldown: 0\n", "actors": [
        ("mortarman", "Marines", 6, 10, 256), ("cryo-pod", "Marines", 2, 2, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    "scenario-ability-aura": {"scripts": ("test-ability-aura",), "drop_conquest": True, "size": (32, 24), "extra_rules": "squad_leader:\n\tActiveAbility@testorder:\n\t\tOrderName: AbilityTestOrder\n\t\tSlot: 8\n\t\tLabel: Move\n\t\tAim: Self\n\t\tCooldown: 100\n\t\tAuraRange: 6c0\n\t\tAuraCondition: order-move\n\t\tAuraDuration: 150\n\t\tShout: MOVE!\n\t\tRing: FFD040\n", "actors": [
        ("squad_leader", "Marines", 8, 10, 256), ("squad_leader", "Marines", 8, 11, 256), ("rifleman", "Marines", 11, 10, 256),
        ("rifleman", "Marines", 18, 10, 256), ("cryo-pod", "Marines", 2, 2, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    "scenario-ability-dash": {"scripts": ("test-ability-dash",), "drop_conquest": True, "size": (32, 24), "extra_rules": "rifleman:\n\tActiveAbility@testdash:\n\t\tOrderName: AbilityTestDash\n\t\tSlot: 8\n\t\tLabel: Dash\n\t\tAim: Target\n\t\tRange: 6c0\n\t\tCooldown: 50\n\t\tChargeDistance: 5c0\n\t\tChargeTicks: 10\n\t\tWeapon: TGMCPunch\n", "actors": [
        ("rifleman", "Marines", 4, 4, 256), ("runner", "Xenos", 6, 5, 768), ("rifleman", "Marines", 4, 10, 256), ("cade", "Marines", 7, 10, 0),
        ("rifleman", "Marines", 27, 16, 256), ("cryo-pod", "Marines", 2, 20, 0), ("resin-silo", "Xenos", 20, 21, 0),
    ]},
    # Autocast (see scenarios/test-ability-autocast.lua): a rifleman throws its frag by itself only once autocast is on. Everyone holds fire.
    "scenario-ability-autocast": {"scripts": ("test-ability-autocast",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("rifleman", "Marines", 6, 10, 768), ("hunter", "Xenos", 11, 10, 0), ("hunter", "Xenos", 11, 11, 0), ("hunter", "Xenos", 12, 10, 0),
        ("cryo-pod", "Marines", 2, 20, 0), ("resin-silo", "Xenos", 28, 21, 0),
    ]},
    # Veterancy (see scenarios/test-veterancy.lua): a rifleman kills three weak runners, worth 150, and ranks up to Veteran (100).
    "scenario-veterancy": {"scripts": ("test-veterancy",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("rifleman", "Marines", 6, 10, 768), ("runner", "Xenos", 9, 10, 0), ("runner", "Xenos", 9, 11, 0), ("runner", "Xenos", 9, 9, 0),
        ("cryo-pod", "Marines", 2, 20, 0), ("resin-silo", "Xenos", 28, 21, 0),
    ]},
    "scenario-kits-marines": {"scripts": ("test-kits-marines",), "drop_conquest": True, "size": (48, 32), "extra_rules": "runner:\n\tHealth:\n\t\tHP: 50000\n", "actors": [
        ("rifleman", "Marines", 6, 10, 512), ("medic", "Marines", 9, 10, 512), ("engineer", "Marines", 12, 10, 512), ("synth", "Marines", 15, 10, 512), ("skirmisher", "Marines", 18, 10, 512), ("smartgunner", "Marines", 21, 10, 512), ("sniper", "Marines", 24, 10, 512), ("rocketeer", "Marines", 27, 10, 512), ("blademan", "Marines", 30, 10, 512), ("mortarman", "Marines", 33, 10, 512), ("flamer", "Marines", 6, 13, 512), ("machinegunner", "Marines", 9, 13, 512), ("bomber", "Marines", 12, 13, 512), ("squad_leader", "Marines", 15, 13, 512), ("field_commander", "Marines", 18, 13, 512), ("grenadier", "Marines", 21, 13, 512), ("mech", "Marines", 24, 13, 512), ("heavygunner", "Marines", 27, 13, 512), ("demolitionist", "Marines", 30, 13, 512), ("mortar-emplacement", "Marines", 8, 20, 0), ("artillery-emplacement", "Marines", 14, 20, 0), ("runner", "Xenos", 8, 16, 0), ("runner", "Xenos", 12, 16, 0), ("runner", "Xenos", 16, 16, 0), ("runner", "Xenos", 20, 16, 0), ("runner", "Xenos", 24, 16, 0), ("runner", "Xenos", 28, 16, 0), ("cryo-pod", "Marines", 3, 3, 0), ("resin-silo", "Xenos", 44, 28, 0),
    ]},
    "scenario-kits-xenos": {"scripts": ("test-kits-xenos",), "drop_conquest": True, "size": (48, 32), "extra_rules": "rifleman:\n\tHealth:\n\t\tHP: 50000\n^Xeno:\n\tPlasma:\n\t\tStartPercent: 100\n\t\tMax: 1000\n", "actors": [
        ("runner", "Xenos", 6, 10, 512), ("hunter", "Xenos", 9, 10, 512), ("sentinel", "Xenos", 12, 10, 512), ("facehugger", "Xenos", 15, 10, 512), ("drone", "Xenos", 18, 10, 512), ("warrior", "Xenos", 21, 10, 512), ("queen", "Xenos", 24, 10, 512), ("spitter", "Xenos", 27, 10, 512), ("praetorian", "Xenos", 30, 10, 512), ("crusher", "Xenos", 33, 10, 512), ("ravager", "Xenos", 6, 13, 512), ("defiler", "Xenos", 9, 13, 512), ("boiler", "Xenos", 12, 13, 512), ("carrier", "Xenos", 15, 13, 512), ("warlock", "Xenos", 18, 13, 512), ("shrike", "Xenos", 21, 13, 512), ("widow", "Xenos", 24, 13, 512), ("wraith", "Xenos", 27, 13, 512), ("bull", "Xenos", 30, 13, 512), ("behemoth", "Xenos", 33, 13, 512), ("mantis", "Xenos", 9, 19, 512), ("baneling", "Xenos", 12, 19, 512), ("defender", "Xenos", 15, 19, 512), ("beetle", "Xenos", 18, 19, 512), ("gorger", "Xenos", 21, 19, 512), ("hivelord", "Xenos", 24, 19, 512), ("puppeteer", "Xenos", 27, 19, 512), ("pyrogen", "Xenos", 30, 19, 512), ("scorpion", "Xenos", 33, 19, 512), ("dragon", "Xenos", 6, 22, 512), ("king", "Xenos", 9, 22, 512), ("larva", "Xenos", 4, 20, 0), ("rifleman", "Marines", 8, 16, 0), ("rifleman", "Marines", 12, 16, 0), ("rifleman", "Marines", 16, 16, 0), ("rifleman", "Marines", 20, 16, 0), ("rifleman", "Marines", 24, 16, 0), ("rifleman", "Marines", 28, 16, 0), ("cryo-pod", "Marines", 44, 28, 0), ("resin-silo", "Xenos", 3, 3, 0),
    ]},
    "scenario-kits-som": {"scripts": ("test-kits-som",), "drop_conquest": True, "size": (48, 32), "extra_rules": "runner:\n\tHealth:\n\t\tHP: 50000\n", "actors": [
        # A beacon for the Blink veteran's Recall.
        ("som-beacon", "Marines", 40, 26, 0),
        ("som_trooper", "Marines", 6, 10, 512), ("som_veteran", "Marines", 9, 10, 512), ("som_corpsman", "Marines", 12, 10, 512), ("som_engineer", "Marines", 15, 10, 512), ("som_squad_leader", "Marines", 18, 10, 512), ("som_field_commander", "Marines", 21, 10, 512), ("som_smartgunner", "Marines", 24, 10, 512), ("som_flamer", "Marines", 27, 10, 512), ("som_grenadier", "Marines", 30, 10, 512), ("som_machinegunner", "Marines", 33, 10, 512), ("som_blademan", "Marines", 6, 13, 512), ("som_scout", "Marines", 9, 13, 512), ("som_mortarman", "Marines", 12, 13, 512), ("som_heavygunner", "Marines", 15, 13, 512), ("som_rocketeer", "Marines", 18, 13, 512), ("som_demolitionist", "Marines", 21, 13, 512), ("som_assault", "Marines", 24, 13, 512), ("som_bomber", "Marines", 27, 13, 512), ("som_mech", "Marines", 30, 13, 512), ("runner", "Xenos", 8, 16, 0), ("runner", "Xenos", 12, 16, 0), ("runner", "Xenos", 16, 16, 0), ("runner", "Xenos", 20, 16, 0), ("runner", "Xenos", 24, 16, 0), ("runner", "Xenos", 28, 16, 0), ("cryo-pod", "Marines", 3, 3, 0), ("resin-silo", "Xenos", 44, 28, 0),
    ]},
    # The bots use the new ability kinds (scenarios/test-ai-kits.lua): squads only, no squad manager, so they fight where they stand.
    "scenario-ai-kits": {"scripts": ("test-ai-kits",), "marine_bot": "skirmish", "xeno_bot": "skirmish", "drop_conquest": True, "size": (40, 28),
                              "extra_rules": "Player:\n\t-SquadManagerBotModule@marines-easy:\n\t-SquadManagerBotModule@marines-normal:\n\t-SquadManagerBotModule@marines-hard:\n\t-SquadManagerBotModule@xenos-easy:\n\t-SquadManagerBotModule@xenos-normal:\n\t-SquadManagerBotModule@xenos-hard:\n^Xeno:\n\tPlasma:\n\t\tStartPercent: 100\n", "actors": [
        ("squad_leader", "Marines", 14, 12, 256), ("rifleman", "Marines", 13, 11, 256), ("rifleman", "Marines", 13, 13, 256),
        ("rifleman", "Marines", 15, 11, 256), ("rifleman", "Marines", 15, 13, 256), ("blademan", "Marines", 16, 12, 256),
        ("bull", "Xenos", 21, 12, 768), ("runner", "Xenos", 20, 11, 768), ("runner", "Xenos", 20, 13, 768), ("runner", "Xenos", 22, 11, 768),
        ("cryo-pod", "Marines", 3, 3, 0), ("resin-silo", "Xenos", 36, 24, 0),
    ]},
    "scenario-ability-silence": {"scripts": ("test-ability-silence",), "drop_conquest": True, "size": (32, 24), "extra_rules": "^Xeno:\n\tPlasma:\n\t\tStartPercent: 100\n", "actors": [
        ("squad_leader", "Marines", 10, 10, 256), ("hunter", "Xenos", 15, 10, 768), ("cryo-pod", "Marines", 2, 2, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    "scenario-engineer-autorepair": {"scripts": ("test-engineer-autorepair",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("engineer", "Marines", 8, 10, 256), ("miner-field", "Neutral", 10, 10, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # A claimed marine miner pays its income (see scenarios/test-miner-income.lua).
    "scenario-miner-income": {"scripts": ("test-miner-income",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("miner", "Marines", 8, 10, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # A miner on a platinum vein pays half as much again (see scenarios/test-miner-platinum.lua).
    "scenario-miner-platinum": {"scripts": ("test-miner-platinum",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("miner", "Marines", 8, 10, 0), ("platinum-vein", "Neutral", 8, 10, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # The economy upgrades (see scenarios/test-miner-upgrades.lua): a miner and the Armory they need.
    "scenario-miner-upgrades": {"scripts": ("test-miner-upgrades",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("miner", "Marines", 8, 10, 0), ("armory", "Marines", 4, 4, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # Stances and retreat for SOM and the xenos, and three command-layer edge cases (see scenarios/test-stance-factions.lua,
    # test-retreat-factions.lua and test-command-edges.lua).
    # Rows are 14 cells apart so a rifle (range 9) cannot reach the next row. The xeno rows start the runner next to its target (melee).
    "scenario-stance-factions": {"scripts": ("test-stance-factions",), "drop_conquest": True, "size": (32, 60), "actors": [
        ("som_trooper", "Marines", 10, 8, 512), ("runner", "Xenos", 13, 8, 0),
        ("som_trooper", "Marines", 10, 22, 512), ("runner", "Xenos", 13, 22, 0),
        ("rifleman", "Marines", 10, 36, 512), ("runner", "Xenos", 11, 36, 0),
        ("rifleman", "Marines", 10, 50, 512), ("runner", "Xenos", 11, 50, 0),
    ]},
    "scenario-shotgun-knockback": {"scripts": ("test-shotgun-knockback",), "drop_conquest": True, "size": (32, 28), "actors": [
        ("skirmisher", "Marines", 8, 8, 256), ("runner", "Xenos", 10, 8, 0),
        ("skirmisher", "Marines", 8, 22, 256), ("warrior", "Xenos", 10, 22, 0),
        ("cryo-pod", "Marines", 4, 4, 0), ("resin-silo", "Xenos", 28, 4, 0),
    ]},
    "scenario-xeno-upgrade": {"scripts": ("test-xeno-upgrade",), "drop_conquest": True, "size": (32, 28), "actors": [
        ("resin-silo", "Xenos", 4, 20, 0), ("evolution-tower", "Xenos", 8, 20, 0), ("maturity-tower", "Xenos", 12, 20, 0),
        ("runner", "Xenos", 4, 6, 0), ("runner", "Xenos", 4, 12, 0), ("cryo-pod", "Marines", 28, 4, 0),
    ]},
    "scenario-ai-engineers": {"scripts": ("test-ai-engineers",), "marine_bot": "skirmish", "drop_conquest": True, "fast": True, "size": (40, 28), "actors": [
        ("cryo-pod", "Marines", 6, 14, 0), ("miner-field", "Neutral", 16, 14, 0), ("resin-silo", "Xenos", 36, 14, 0),
    ]},
    # Starts with 2000: on the base trickle alone the bot sometimes had no cash left for the second rifle step in 9000 ticks.
    "scenario-ai-upgrade": {"scripts": ("test-ai-upgrade",), "marine_bot": "skirmish", "drop_conquest": True, "fast": True, "size": (32, 28),
                            "extra_rules": "Player:\n\tPlayerResources:\n\t\tDefaultCash: 2000\n", "actors": [
        ("cryo-pod", "Marines", 6, 4, 0), ("armory", "Marines", 12, 4, 0), ("rifleman", "Marines", 8, 8, 256),
        # Miners are capture points now: the bot's income is the ore fields it claims, so the map needs some.
        ("miner-field", "Neutral", 10, 10, 0), ("miner-field", "Neutral", 16, 8, 0),
        ("resin-silo", "Xenos", 28, 24, 0),
    ]},
    "scenario-upgrade": {"scripts": ("test-upgrade",), "drop_conquest": True, "size": (32, 28), "actors": [
        ("cryo-pod", "Marines", 6, 4, 0), ("armory", "Marines", 12, 4, 0),
        ("rifleman", "Marines", 8, 8, 256), ("runner", "Xenos", 14, 14, 0),
        ("rifleman", "Marines", 4, 8, 256), ("runner", "Xenos", 11, 15, 0), ("resin-silo", "Xenos", 28, 24, 0),
    ]},
    "scenario-upgrade-ladders": {"scripts": ("test-upgrade-ladders",), "drop_conquest": True, "size": (32, 28), "actors": [
        ("cryo-pod", "Marines", 6, 4, 0), ("armory", "Marines", 12, 4, 0), ("ordnance-depot", "Marines", 16, 4, 0), ("workshop", "Marines", 20, 4, 0),
        ("machinegunner", "Marines", 4, 10, 256), ("crusher", "Xenos", 14, 11, 0), ("crusher", "Xenos", 14, 12, 0),
        ("medic", "Marines", 4, 26, 256), ("engineer", "Marines", 6, 26, 256), ("rocketeer", "Marines", 8, 26, 256),
        ("skirmisher", "Marines", 10, 26, 256), ("field_commander", "Marines", 12, 26, 256), ("sniper", "Marines", 14, 26, 256), ("flamer", "Marines", 16, 26, 256), ("resin-silo", "Xenos", 28, 24, 0),
    ]},
    "scenario-gasmask": {"scripts": ("test-gasmask",), "drop_conquest": True, "size": (32, 28), "actors": [
        ("cryo-pod", "Marines", 6, 4, 0), ("armory", "Marines", 16, 4, 0),
        ("rifleman", "Marines", 8, 14, 256), ("rifleman", "Marines", 8, 20, 256),
        ("resin-silo", "Xenos", 28, 24, 0),
    ]},
    "scenario-synth": {"scripts": ("test-synth",), "drop_conquest": True, "size": (32, 28), "actors": [
        ("cryo-pod", "Marines", 6, 4, 0), ("armory", "Marines", 16, 4, 0),
        ("synth", "Marines", 12, 8, 256), ("rifleman", "Marines", 10, 8, 256), ("runner", "Xenos", 13, 8, 0),
        ("resin-silo", "Xenos", 28, 24, 0),
    ]},
    "scenario-synth-infest": {"scripts": ("test-synth-infest",), "drop_conquest": True, "size": (32, 28), "actors": [
        ("cryo-pod", "Marines", 6, 4, 0),
        ("rifleman", "Marines", 10, 8, 256), ("facehugger", "Xenos", 11, 8, 0),
        ("synth", "Marines", 10, 20, 256), ("facehugger", "Xenos", 11, 20, 0),
        ("resin-silo", "Xenos", 28, 24, 0),
    ]},
    "scenario-weed-bash": {"scripts": ("test-weed-bash",), "drop_conquest": True, "size": (32, 60), "actors": [
        ("rifleman", "Marines", 10, 8, 512), ("weed-node", "Xenos", 13, 8, 0),
        ("rifleman", "Marines", 5, 22, 512), ("weed-node", "Xenos", 15, 22, 0),
        ("rifleman", "Marines", 5, 36, 512), ("weed-node", "Xenos", 15, 36, 0),
        ("resin-silo", "Xenos", 28, 52, 0), ("cryo-pod", "Marines", 4, 52, 0),
    ]},
    "scenario-retreat-factions": {"scripts": ("test-retreat-factions",), "drop_conquest": True, "actors": [
        ("som_trooper", "Marines", 4, 4, 512), ("cryo-pod", "Marines", 16, 4, 0),
        ("runner", "Xenos", 4, 16, 0), ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    "scenario-command-edges": {"scripts": ("test-command-edges",), "drop_conquest": True, "size": (32, 28), "actors": [
        ("rifleman", "Marines", 4, 4, 512), ("cryo-pod", "Marines", 16, 16, 0), ("squad_leader", "Marines", 4, 10, 256),
        ("resin-silo", "Xenos", 28, 24, 0),
    ]},
    # A friendly blast hurts an ally but raises no under-attack alert (same layout as scenario-explosive).
    # The crusher must outlive the test: dead, it leaves an acid pool whose (enemy) burns would raise a real alert.
    "scenario-friendly-fire-alert": {"scripts": ("test-friendly-fire-alert",), "extra_rules": "crusher:\n\tHealth:\n\t\tHP: 20000\n", "actors": [
        ("demolitionist", "Marines", 10, 10, 512),
        ("demolitionist", "Marines", 15, 11, 512),
        ("rifleman", "Marines", 15, 9, 512),
        ("crusher", "Xenos", 15, 10, 0),
        ("rifleman", "Marines", 20, 20, 0),
        ("resin-silo", "Xenos", 19, 19, 0),
    ]},
    # A disabled marine miner pays nothing and is never destroyed (see scenarios/test-miner-disabled-income.lua).
    "scenario-miner-disabled-income": {"scripts": ("test-miner-disabled-income",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("miner", "Marines", 8, 10, 0), ("hunter", "Xenos", 9, 10, 0),
    ]},
    # The same with a miner so weak that one claw hit would take it to 0: the hit is cut down at the floor, the miner lives.
    "scenario-miner-big-hit": {"scripts": ("test-miner-disabled-income",), "drop_conquest": True, "size": (32, 24),
                               "extra_rules": "miner:\n\tHealth:\n\t\tHP: 20\n", "actors": [
        ("miner", "Marines", 8, 10, 0), ("hunter", "Xenos", 9, 10, 0),
    ]},
    # A sentry turret against one runner, and against three (see scenarios/test-turret-holds.lua).
    "scenario-turret-1": {"scripts": ("test-turret-holds",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("sentry-turret", "Marines", 10, 10, 0), ("runner", "Xenos", 18, 10, 256),
    ]},
    "scenario-turret-3": {"scripts": ("test-turret-holds",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("sentry-turret", "Marines", 10, 10, 0), ("runner", "Xenos", 18, 9, 256), ("runner", "Xenos", 18, 10, 256), ("runner", "Xenos", 18, 11, 256),
    ]},
    # A xeno runner disables an unclaimed ore field (see scenarios/test-field-contest.lua).
    "scenario-field-contest": {"scripts": ("test-field-contest",), "size": (32, 24), "drop_conquest": True, "actors": [
        ("runner", "Xenos", 8, 10, 256), ("miner-field", "Neutral", 11, 10, 0), ("engineer", "Marines", 28, 20, 0),
    ]},
    # The landing intro (FactionStart): the squad rides the Alamo down and walks out; the buildings stand from the start
    # (see scenarios/test-landing-intro.lua).
    "scenario-landing-intro": {"scripts": ("test-landing-intro",), "size": (32, 40), "spawns": [(16, 24), (28, 36)], "drop_conquest": True,
                               "extra_rules": "World:\n\tFactionStart:\n\t\tMarines: cryo-pod|-2|-2|512, rifleman|0|2|256, rifleman|1|2|256, medic|0|3|256\n",
                               "actors": [("rifleman", "Marines", 16, 26, 256), ("resin-silo", "Xenos", 28, 36, 0)]},
    # The order a right-click gives: engineer on a damaged miner and on a free field, drone on a free field (see scenarios/test-click-repair.lua).
    "scenario-click-repair": {"scripts": ("test-click-repair",), "size": (32, 24), "drop_conquest": True, "actors": [
        ("engineer", "Marines", 8, 10, 256), ("rifleman", "Marines", 8, 12, 256), ("miner-field", "Neutral", 10, 14, 0), ("miner", "Marines", 10, 14, 0),
        ("miner-field", "Neutral", 12, 10, 0), ("drone", "Xenos", 14, 10, 256), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # The SOM blade unit's blink drive (see scenarios/test-blink.lua).
    "scenario-blink": {"scripts": ("test-blink",), "size": (32, 24), "drop_conquest": True, "human_faction": "som", "actors": [
        ("som_blademan", "Marines", 8, 10, 256), ("hunter", "Xenos", 14, 10, 768), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # Portal, Rewind and Drain (see scenarios/test-xeno-kit.lua).
    "scenario-xeno-kit": {"scripts": ("test-xeno-kit",), "size": (32, 24), "drop_conquest": True, "actors": [
        ("wraith", "Xenos", 8, 6, 256), ("runner", "Xenos", 4, 6, 256), ("wraith", "Xenos", 8, 12, 256), ("rifleman", "Marines", 11, 12, 256),
        ("gorger", "Xenos", 8, 18, 256), ("rifleman", "Marines", 9, 18, 256), ("resin-silo", "Xenos", 28, 20, 0), ("cryo-pod", "Marines", 26, 4, 0),
    ]},
    # What the newer xeno abilities do, one caste per row (see scenarios/test-xeno-kit2.lua).
    "scenario-xeno-kit2": {"scripts": ("test-xeno-kit2",), "size": (48, 32), "drop_conquest": True,
                           "extra_rules": "rifleman:\n\tHealth:\n\t\tHP: 5000\n^Xeno:\n\tPlasma:\n\t\tStartPercent: 100\n\t\tMax: 1000\n", "actors": [
        ("warrior", "Xenos", 8, 4, 256), ("rifleman", "Marines", 9, 4, 256), ("shrike", "Xenos", 8, 7, 256), ("rifleman", "Marines", 7, 7, 256),
        ("rifleman", "Marines", 9, 7, 256), ("behemoth", "Xenos", 8, 10, 256), ("hunter", "Xenos", 8, 13, 256), ("defender", "Xenos", 8, 16, 256),
        ("gorger", "Xenos", 8, 19, 256), ("runner", "Xenos", 10, 19, 256), ("queen", "Xenos", 8, 22, 256), ("drone", "Xenos", 10, 22, 256),
        ("puppeteer", "Xenos", 8, 25, 256), ("widow", "Xenos", 8, 28, 256), ("dragon", "Xenos", 24, 6, 256), ("rifleman", "Marines", 25, 6, 256),
        ("resin-silo", "Xenos", 42, 26, 0), ("cryo-pod", "Marines", 42, 4, 0),
    ]},
    # Weeds as territory: the node gate on tier 3 castes, a corrupted miner fed by weeds, fire burning weeds (see scenarios/test-territory.lua).
    "scenario-territory": {"scripts": ("test-territory",), "size": (40, 24), "drop_conquest": True, "actors": [
        ("resin-silo", "Xenos", 34, 18, 0), ("evolution-tower", "Xenos", 34, 4, 0), ("warrior", "Xenos", 4, 4, 256),
        ("weed-node", "Xenos", 14, 4, 0), ("weed-node", "Xenos", 20, 4, 0), ("weed-node", "Xenos", 26, 4, 0),
        ("corrupted-miner", "Xenos", 8, 18, 0), ("weeds", "Xenos", 9, 18, 0),
        ("weeds", "Xenos", 20, 14, 0), ("weeds", "Xenos", 26, 14, 0), ("flame-patch", "Marines", 20, 14, 0), ("rifleman", "Marines", 38, 12, 0),
    ]},
    # The second-wave upgrades: prerequisites, Thick Weeds and Sticky Weeds (see scenarios/test-upgrades2.lua). Two strips of weeds for
    # the two marines to cross (off the spawn row; a weed strip over a spawn cell was checked on 2026-11-17 and loads fine), and one cell under the runner.
    "scenario-upgrades2": {"scripts": ("test-upgrades2",), "size": (40, 24), "drop_conquest": True, "actors": [
        ("resin-silo", "Xenos", 34, 18, 0), ("cryo-pod", "Marines", 32, 2, 0), ("runner", "Xenos", 6, 20, 256), ("weeds", "Xenos", 6, 20, 0),
        ("rifleman", "Marines", 6, 5, 768), ("rifleman", "Marines", 6, 11, 768),
        ("weeds", "Xenos", 6, 5, 0), ("weeds", "Xenos", 7, 5, 0), ("weeds", "Xenos", 8, 5, 0), ("weeds", "Xenos", 9, 5, 0), ("weeds", "Xenos", 10, 5, 0), ("weeds", "Xenos", 11, 5, 0), ("weeds", "Xenos", 12, 5, 0), ("weeds", "Xenos", 13, 5, 0), ("weeds", "Xenos", 14, 5, 0), ("weeds", "Xenos", 15, 5, 0), ("weeds", "Xenos", 16, 5, 0), ("weeds", "Xenos", 17, 5, 0), ("weeds", "Xenos", 18, 5, 0), ("weeds", "Xenos", 6, 11, 0), ("weeds", "Xenos", 7, 11, 0), ("weeds", "Xenos", 8, 11, 0), ("weeds", "Xenos", 9, 11, 0), ("weeds", "Xenos", 10, 11, 0), ("weeds", "Xenos", 11, 11, 0), ("weeds", "Xenos", 12, 11, 0), ("weeds", "Xenos", 13, 11, 0), ("weeds", "Xenos", 14, 11, 0), ("weeds", "Xenos", 15, 11, 0), ("weeds", "Xenos", 16, 11, 0), ("weeds", "Xenos", 17, 11, 0), ("weeds", "Xenos", 18, 11, 0), 
    ]},
    # SOM heat, Recall and the beacon's drop pod bonus (see scenarios/test-som-kit.lua).
    "scenario-som-kit": {"scripts": ("test-som-kit",), "drop_conquest": True, "size": (48, 24), "human_faction": "som",
                         "extra_rules": "runner:\n\tHealth:\n\t\tHP: 5000\n", "actors": [
        ("cryo-pod", "Marines", 4, 4, 0), ("som-beacon", "Marines", 10, 16, 0), ("som_blademan", "Marines", 42, 4, 256),
        ("som_trooper", "Marines", 24, 12, 768), ("runner", "Xenos", 28, 12, 256), ("resin-silo", "Xenos", 42, 18, 0),
    ]},
    # Formation movement: a fast and a slow unit sent to one cell arrive together and in shape (see scenarios/test-formation.lua).
    "scenario-formation": {"scripts": ("test-formation",), "size": (40, 24), "drop_conquest": True, "actors": [
        ("runner", "Xenos", 6, 10, 768), ("crusher", "Xenos", 6, 12, 768), ("resin-silo", "Xenos", 34, 18, 0), ("rifleman", "Marines", 2, 2, 0),
    ]},
    # Downed marines: a runner brings a rifleman down; a corpsman revives him, the runner cocoons him, or he bleeds out
    # (see scenarios/test-downed.lua). A spare rifleman far off and a silo keep either side from losing early.
    **{f"scenario-downed-{mode}": {"scripts": (f"mode-downed-{mode}", "test-downed"), "size": (32, 24), "drop_conquest": True, "actors": [
        ("rifleman", "Marines", 10, 10, 512), ("rifleman", "Marines", 28, 2, 0), ("runner", "Xenos", 12, 10, 256),
        ("resin-silo", "Xenos", 28, 20, 0), *([("medic", "Marines", 6, 14, 768)] if mode == "revive" else []),
    ]} for mode in ("revive", "cocoon", "bleed")},
    # Distress Signal: riflemen hold the three disk terminals, then the nuke, which goes off and ends the hive (see scenarios/test-distress.lua).
    # One rifleman waits at the nuke from the start: it must not arm before the terminals are decoded.
    "scenario-distress": {"scripts": ("test-distress",), "size": (40, 24), "drop_conquest": True,
                          "extra_rules": "World:\n\tTgmcOptions:\n\t\tObjectiveDefault: distress\n", "actors": [
        ("disk-terminal", "Neutral", 6, 4, 0), ("disk-terminal", "Neutral", 6, 20, 0), ("disk-terminal", "Neutral", 20, 4, 0),
        ("nuke", "Neutral", 30, 12, 0), ("rifleman", "Marines", 7, 4, 0), ("rifleman", "Marines", 7, 20, 0), ("rifleman", "Marines", 21, 4, 0),
        ("rifleman", "Marines", 31, 12, 0), ("resin-silo", "Xenos", 36, 21, 0), ("runner", "Xenos", 37, 21, 0),
    ]},
    # Colony doors: a runner has to pry one open (see scenarios/test-door-pry.lua), timed against the same door with the pry off.
    **{f"scenario-door-pry-{m}": {"scripts": (f"mode-door-pry-{m}", "test-door-pry"), "drop_conquest": True, "size": (32, 24), "ground": "doorline",
                                  "extra_rules": "" if m == "on" else "^MapDoor:\n\tMapDoor:\n\t\tPryTicks: 0\n", "actors": [
        ("rifleman", "Marines", 2, 2, 0), ("mapdoor-0", "Neutral", 14, 11, 0), ("runner", "Xenos", 8, 11, 256), ("resin-silo", "Xenos", 28, 20, 0),
    ]} for m in ("on", "off")},
    # Geothermal generators: an engineer repairs one, a drone corrupts the other (see scenarios/test-geothermal.lua).
    "scenario-geothermal": {"scripts": ("test-geothermal",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("engineer", "Marines", 8, 10, 256), ("geothermal-field", "Neutral", 10, 10, 0), ("cryo-pod", "Marines", 3, 3, 0),
        ("drone", "Xenos", 24, 10, 768), ("geothermal-field", "Neutral", 22, 10, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # Landing delay: the first minute keeps a rifleman at his landing zone (see scenarios/test-landing-leash.lua).
    "scenario-landing-leash": {"scripts": ("test-landing-leash",), "drop_conquest": True, "size": (48, 24),
                               "extra_rules": "World:\n\tTgmcOptions:\n\t\tLandingDelayDefault: 30\n", "actors": [
        ("rifleman", "Marines", 6, 12, 256), ("cryo-pod", "Marines", 4, 4, 0), ("resin-silo", "Xenos", 44, 20, 0),
    ]},
    # Crash: the clock runs out with the nuke untouched, and the marines are gone (see scenarios/test-crash.lua).
    "scenario-crash": {"scripts": ("test-crash",), "drop_conquest": True, "size": (40, 24),
                       "extra_rules": "World:\n\tTgmcOptions:\n\t\tObjectiveDefault: crash\n\tCrashTimer:\n\t\tTimeLimit: 600\n", "actors": [
        ("rifleman", "Marines", 6, 12, 0), ("rifleman", "Marines", 8, 12, 0), ("nuke", "Neutral", 30, 12, 0), ("resin-silo", "Xenos", 36, 20, 0),
    ]},
    # Crash sweep (Not a test, run by mod/shots.sh): every unit and structure of the rules stands on one map, owned by the player, and
    # ScreenshotAt's Sweep selects each in turn with the HUD drawn. The actors are filled in by sweep_actors() below.
    "shot-sweep": {"scripts": ("shot",), "size": (96, 72), "drop_conquest": True,
                   "extra_rules": "World:\n\tScreenshotAt:\n\t\tSweep: true\n^Unit:\n\tAutoTarget:\n\t\tInitialStance: HoldFire\n", "actors": "sweep"},
    # The rosters: what each human faction can build with every tech building standing (see scenarios/test-roster.lua).
    "scenario-roster": {"scripts": ("test-roster",), "size": (32, 24), "drop_conquest": True, "actors": [("cryo-pod", "Marines", 6, 6, 0), ("armory", "Marines", 10, 6, 0), ("medbay", "Marines", 14, 6, 0), ("ordnance-depot", "Marines", 18, 6, 0), ("workshop", "Marines", 22, 6, 0), ("resin-silo", "Xenos", 28, 20, 0)]},
    "scenario-roster-som": {"scripts": ("test-roster",), "size": (32, 24), "drop_conquest": True, "human_faction": "som", "actors": [("cryo-pod", "Marines", 6, 6, 0), ("armory", "Marines", 10, 6, 0), ("medbay", "Marines", 14, 6, 0), ("ordnance-depot", "Marines", 18, 6, 0), ("workshop", "Marines", 22, 6, 0), ("resin-silo", "Xenos", 28, 20, 0)]},
    # Capture points: a drone corrupts a free field, riflemen free it, an engineer claims it (see scenarios/test-capture.lua).
    "scenario-capture": {"scripts": ("test-capture",), "size": (32, 24), "drop_conquest": True, "actors": [
        ("drone", "Xenos", 14, 10, 256), ("miner-field", "Neutral", 16, 10, 0), ("engineer", "Marines", 24, 12, 0),
        ("rifleman", "Marines", 22, 9, 768), ("rifleman", "Marines", 22, 10, 768), ("rifleman", "Marines", 22, 11, 768),
        ("resin-silo", "Xenos", 4, 20, 0),
    ]},
    # An engineer repairs an ore field: it turns into the marines' miner (see scenarios/test-miner-field.lua).
    "scenario-miner-field": {"scripts": ("test-miner-field",), "size": (32, 24), "drop_conquest": True, "actors": [
        ("engineer", "Marines", 8, 10, 256), ("miner-field", "Neutral", 11, 10, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    "scenario-objects-damage": {"scripts": ("test-objects-damage",), "size": (32, 24), "drop_conquest": True, "actors": [
        ("rifleman", "Marines", 8, 10, 256), ("mapobj-0", "Neutral", 11, 10, 0),
        ("spitter", "Xenos", 20, 10, 768), ("mapobj-1", "Neutral", 17, 10, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # A bomb run knocks a wall down (see scenarios/test-walls.lua): a wall of three cells thick, the CAS depot beside it.
    "scenario-walls": {"scripts": ("test-walls",), "drop_conquest": True, "size": (32, 24), "ground": "walls", "actors": [
        ("ordnance-depot", "Marines", 6, 6, 0), ("rifleman", "Marines", 10, 12, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # Every explosion chips walls (see scenarios/test-wall-grenade.lua): grenades on a resin wall that stands against it.
    "scenario-wall-grenade": {"scripts": ("test-wall-grenade",), "drop_conquest": True, "size": (32, 24), "ground": "walls",
                              "extra_rules": "resin-wall:\n\tHealth:\n\t\tHP: 30000\n", "actors": [
        ("grenadier", "Marines", 7, 10, 0), ("grenadier", "Marines", 7, 11, 0), ("grenadier", "Marines", 7, 12, 0),
        ("resin-wall", "Xenos", 13, 11, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # Unit control: what a click orders on an enemy, the ground, a fence and a wall cell (see scenarios/test-click-force.lua).
    "scenario-click-force": {"scripts": ("test-click-force",), "drop_conquest": True, "size": (32, 24), "ground": "walls", "actors": [
        ("rifleman", "Marines", 8, 10, 256), ("grenadier", "Marines", 10, 11, 256), ("hunter", "Xenos", 8, 16, 0),
        ("prop:fence_ns", "Neutral", 6, 12, 0), ("resin-silo", "Xenos", 28, 20, 0),
    ]},
    # The heavy castes break fences by walking through them (see scenarios/test-fence-smash.lua). "prop:" names a built-map prop.
    "scenario-fence-smash": {"scripts": ("test-fence-smash",), "drop_conquest": True, "size": (32, 24), "actors": [
        ("crusher", "Xenos", 6, 8, 0), ("hunter", "Xenos", 6, 14, 0), ("rifleman", "Marines", 28, 20, 0),
    ] + [("prop:fence_ns", "Neutral", 14, y, 0) for y in range(1, 23)]},
    # The only support power building dies with the HUD drawn (see scenarios/test-power-lost.lua).
    "scenario-power-lost": {"scripts": ("test-power-lost",), "drop_conquest": True, "actors": [
        ("ordnance-depot", "Marines", 6, 6, 0), ("rifleman", "Marines", 10, 12, 0), ("resin-silo", "Xenos", 19, 19, 0),
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


SOM_UNITS = {"rifleman": "som_trooper", "medic": "som_corpsman", "engineer": "som_engineer"}
# The four-base (free-for-all) big maps: one slot per base, spawn 1 to 4 in this order. Random picks one of the three factions at the start.
FOUR_PLAYERS = [("Marines", "marines"), ("Xenos", "xenos"), ("Som", "som"), ("Random", "Random")]


def pick_extra_spawns(land, taken, count, radius=6):
    """Start cells for the extra bases of a four-base map: the open cells farthest from every base taken so far, where the square of
    radius cells around them is at least 90% ground. Rock inside that square is cleared to dirt, so FactionStart can place its buildings."""
    h, w = len(land), len(land[0])
    sums = [[0] * (w + 1) for _ in range(h + 1)]
    for y in range(h):
        for x in range(w):
            sums[y + 1][x + 1] = sums[y][x + 1] + sums[y + 1][x] - sums[y][x] + (land[y][x] in "GDF")
    side = 2 * radius + 1
    chosen = []
    for _ in range(count):
        best = None
        for y in range(radius + 1, h - radius - 1):
            for x in range(radius + 1, w - radius - 1):
                x0, y0 = x - radius, y - radius
                ground = sums[y0 + side][x0 + side] - sums[y0][x0 + side] - sums[y0 + side][x0] + sums[y0][x0]
                if ground < 0.9 * side * side:
                    continue
                d = min((x - a) ** 2 + (y - b) ** 2 for a, b in taken + chosen)
                if best is None or d > best[0]:
                    best = (d, x, y)
        assert best is not None, "no open ground left for another base"
        chosen.append((best[1], best[2]))
    for x, y in chosen:
        for ax in range(x - radius, x + radius + 1):
            for ay in range(y - radius, y + radius + 1):
                if land[ay][ax] == "R":
                    land[ay][ax] = "D"
    return chosen


def faction_start_rules():
    """The World rules of FactionStart (tgmc/code/FactionStart.cs): what each faction starts with, around its start location. Taken from the
    Landing Zone layout: the marine side relative to (6, 14), the xeno side relative to (33, 13); SOM gets the marine buildings and its own troops."""
    def entries(owner, cx, cy, swap=None):
        out = []
        for name, o, x, y, facing in LANDING_ZONE:
            if o == owner:
                out.append(f"{(swap or {}).get(name, name)}|{x - cx}|{y - cy}|{facing}")
        return ", ".join(out)
    return ("World:\n\tFactionStart:\n\t\tMarines: " + entries("Marines", 6, 14) + "\n\t\tSom: " + entries("Marines", 6, 14, SOM_UNITS)
            + "\n\t\tXenos: " + entries("Xenos", 33, 13) + "\n")


def write_map(folder, title, size_w, size_h, placed, visibility, spawns, scripts=(), ground=flat_ground,
              category="Skirmish", drop_conquest=False, xeno_bot=None, marine_bot=None, fast=False, extra_rules="",
              music=False, faction_start=False, players=None, brief="", human_faction="marines"):
    # A scenario map has no slot for the xenos: they are a scripted player, so Lua can find them and they never act.
    os.makedirs(folder, exist_ok=True)
    cells = size_w * size_h
    # map.bin: version byte, width, height, u32 tiles offset, u32 heights offset (0), u32 resources offset (0),
    # then per cell (x-major): u16 template id, u8 variant index.
    header = struct.pack("<BHHIII", 2, size_w, size_h, 17, 0, 0)
    def tile(x, y):
        # Water, ford and dirt show grass along each side and corner that has grass beyond it: the variant index is the frame
        # of the tile's edge sheet (mod/build_tileset.py, edge_frame).
        template, index = ground(x, y)
        if template == GRASS:
            # Patches of the second grass tile three cells across, and one cell in twelve with a piece of flora on it
            # (frames of grass-var.png). A fixed scramble of the position, so a map builds the same every time.
            def scramble(a, b):
                n = (a * 374761393 + b * 668265263) & 0xFFFFFFFF
                n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
                return n ^ (n >> 16)
            h = scramble(x, y)
            index = 2 + h // 14 % (build_tileset.GRASS_FRAMES - 2) if h % 14 == 0 else scramble(x // 3, y // 3) % 3 == 0
        if template in (WATER, FORD, DIRT):
            def grass(dx, dy):
                nx, ny = x + dx, y + dy
                return 0 <= nx < size_w and 0 <= ny < size_h and ground(nx, ny)[0] == GRASS
            index = build_tileset.edge_frame(grass)
        if template in (ROCK, WALL):
            # Rock joins rock, wall and the map edge: the frame is TGMC's cave piece for that set of neighbours.
            def rock(dx, dy):
                nx, ny = x + dx, y + dy
                return not (0 <= nx < size_w and 0 <= ny < size_h) or ground(nx, ny)[0] in (ROCK, WALL)
            index = build_tileset.cave_frame(rock)
        return template, index

    body = b"".join(struct.pack("<HB", *tile(x, y)) for x in range(size_w) for y in range(size_h))
    with open(os.path.join(folder, "map.bin"), "wb") as f:
        f.write(header + body)

    actors = []
    # Spawn points come first so that Spawn: 1 and 2 on the players below are their indices.
    if faction_start:
        # The factions place their own start (FactionStart): the map keeps only what is neutral.
        placed = [a for a in placed if a[1] not in ("Marines", "Xenos")]
        extra_rules += faction_start_rules()
    if "Lobby" in visibility:
        # What the map picker shows under the preview (MapBrief, read by MapPickerInfoLogic).
        brief = brief or ("A wave mission: hold out against the hive." if "MissionSelector" in visibility else "Built for this mod: open ground, a base at each end.")
        extra_rules += f"World:\n\tMapBrief:\n\t\tOreFields: {sum(a[0] == 'miner-field' for a in placed)}\n\t\tDescription: {brief}\n"
    placed = [("mpspawn", "Neutral", x, y, 0) for x, y in spawns] + list(placed)
    for i, (name, owner, x, y, facing) in enumerate(placed):
        actors.append(f"\tActor{i}: {name}\n\t\tOwner: {owner}\n\t\tLocation: {x},{y}\n\t\tFacing: {facing}\n")

    script = bool(scripts)
    rules_line = ""
    if scripts or faction_start or extra_rules:
        rules_line = "Rules: rules.yaml\n\n"
        listed = [f"{name}.lua" for name in scripts]
        if music:
            # A map's Scripts replaces the world's, which holds the music script. It goes last: it wraps the map's WorldLoaded.
            listed.append("tgmc|scripts/music.lua")
        rules = ("World:\n\tLuaScript:\n\t\tScripts: " + ", ".join(listed) + "\n") if scripts else ""
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
    # A bot written into the map has no lobby slot to give it a spawn point: FactionStart needs its home said here.
    if faction_start and xeno_bot:
        xeno_bot_line += f"\t\tHomeLocation: {spawns[1][0]},{spawns[1][1]}\n"
    # The lobby maps let each side pick its faction (marines, SOM or xenos); scenario maps keep them fixed.
    lock_faction = "False" if "Lobby" in visibility else "True"
    marine_bot_line = f"\t\tBot: {marine_bot}\n" if marine_bot else ""
    if faction_start and marine_bot:
        marine_bot_line += f"\t\tHomeLocation: {spawns[0][0]},{spawns[0][1]}\n"
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
{marine_bot_line}		Faction: {human_faction}
		LockFaction: {lock_faction}
		Enemies: Xenos
		Spawn: 1
		LockSpawn: True
	PlayerReference@Xenos:
		Name: Xenos
		Playable: {not script}
{xeno_bot_line}		Faction: xenos
		LockFaction: {lock_faction}
		Enemies: Marines
		Spawn: 2
		LockSpawn: True
{observer_block}
Actors:
{"".join(actors)}"""
    if not marine_bot and not script:
        # Both sides are open slots: an Enemies line would override the lobby's teams (it made teammates fight). With a script or a bot-only side the line stays, because the engine makes slots without a lobby client neutral.
        yaml = re.sub(r"\t\tEnemies: .*\n", "", yaml)
    if players:
        # Replace the Marines, Xenos and observer slots with one playable slot per (name, faction). No Enemies line: the lobby's teams decide who is whose ally (team 0 is everyone for themselves).
        slots = "".join(
            f"\tPlayerReference@{name}:\n\t\tName: {name}\n\t\tPlayable: True\n\t\tFaction: {faction}\n\t\tLockFaction: False\n"
            f"\t\tSpawn: {i}\n\t\tLockSpawn: True\n"
            for i, (name, faction) in enumerate(players, 1))
        yaml, swapped = re.subn(r"\tPlayerReference@Marines:.*?(?=\nActors:)", lambda m: slots, yaml, count=1, flags=re.S)
        assert swapped, f"{title}: the Marines slot was not found, so the player slots were not replaced"
    with open(os.path.join(folder, "map.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(yaml)

    colours = {ROCK: (0x3A, 0x3A, 0x3A, 255), WALL: (0x48, 0x48, 0x4C, 255), GRASS: (0x2E, 0x52, 0x30, 255), WATER: (0x1C, 0x3A, 0x5E, 255), FORD: (0x4A, 0x72, 0x86, 255), DIRT: (0x7A, 0x62, 0x40, 255)}
    preview = Image.new("RGBA", (size_w, size_h))
    preview.putdata([colours.get(ground(x, y)[0]) or build_maptiles.COLOURS[ground(x, y)[0]] for y in range(size_h) for x in range(size_w)])
    preview.save(os.path.join(folder, "map.png"))


def ore_fields(tgmc, spec, kind="/obj/machinery/miner"):
    """The cells of a converted map's ore fields (TGMC's ore drills), in the cells tgmc_dmm.load makes: the same crop, shrunk by the factor.
    `kind` narrows it to one drill type, such as the platinum ones."""
    path = os.path.join(tgmc, spec["file"])
    width, height, grid = tgmc_dmm.parse(path)
    _, _, things = tgmc_dmm.parse_objects(path)
    f = spec["factor"]
    x0, y0, _, _ = tgmc_dmm.crop_box(grid, width, height, f)
    cells = set()
    for x in range(x0, width):
        for y in range(y0, height):
            if any(p.startswith(kind) for p, _ in things[x][y]):
                cells.add(((x - x0) // f, (y - y0) // f))
    return sorted(cells)


def distress_objective(reach, nukes, towers, bases, taken):
    """TGMC's Distress Signal points (the lobby's Objective, HoldObjective in tgmc/code/Objective.cs): the nuke where TGMC spawns it
    (else halfway between the first two bases) and three disk terminals at TGMC's sensor tower spots, spread out: each the spot
    furthest from the nuke and the terminals already placed. All on ground the marine base reaches, 8 or more cells from every base
    and off the cells other map actors (ore fields, props) already use."""
    def dist(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    ok = [c for c in sorted(reach) if c not in taken and all(max(abs(c[0] - b[0]), abs(c[1] - b[1])) >= 8 for b in bases)]
    if not ok:
        return []
    near = lambda p: min(ok, key=lambda c: dist(c, p))  # noqa: E731
    mid = ((bases[0][0] + bases[1][0]) // 2, (bases[0][1] + bases[1][1]) // 2)
    nuke = near(nukes[0] if nukes else mid)
    # Too few tower spots: every fourth reachable cell stands in for the rest.
    spots = sorted({near(t) for t in towers}) or ok[::4]
    if len(spots) < 3:
        spots += ok[::4]
    picked = []
    for _ in range(3):
        free = [c for c in spots if c != nuke and c not in picked]
        if not free:
            break
        picked.append(max(free, key=lambda c: min(dist(c, o) for o in [nuke] + picked)))
    return [("nuke", "Neutral", nuke[0], nuke[1], 0)] + [("disk-terminal", "Neutral", x, y, 0) for x, y in picked]


def camo_rules(style, weather=None):
    """The map's camo for the marines' standard armour (TgmcCamo): TGMC's style for that map, or "" for the plain set. With `weather`,
    also the map's default weather in the lobby (tgmc_dmm.WEATHER). One World block, since a rules file may name World only once."""
    rules = f"World:\n\tTgmcCamo:\n\t\tStyle: {style}\n"
    # TGMC's maps hold the marines at their landing zone for the first minute (the lobby's Landing Delay), as its fog walls do.
    rules += "\tTgmcOptions:\n\t\tLandingDelayDefault: 60\n"
    if weather:
        rules += f"\t\tWeatherDefault: {weather}\n"
    return rules


def write_tgmc_map(folder, title, rows, marines, xenos, art=None, objects=None, open_variant=None, ai_test=False, fields=(), bases=2, camo="", platinum=(),
                   nukes=(), towers=(), weather=None, generators=(), mission=None):
    """A skirmish map from a converted TGMC map. Landing Zone's two bases go at the given centres, on open ground. With `art`, a function
    (x, y) -> template id (build_maptiles), a cell that was not changed shows its real TGMC picture; a carved or cleared cell shows plain dirt."""
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
    # A four-base map adds bases with no pre-placed actors: FactionStart gives each playable slot its faction's start at its spawn.
    extra_spawn = pick_extra_spawns(land, [spawn_m, spawn_x], bases - 2)
    # The bases must be joined by walkable ground, or the match can never be won. Where TGMC's own walls cut them apart (the
    # full size maps keep every wall), dig the cheapest tunnel through the rock: open ground costs 1, rock 6.
    import heapq
    walk = "GDF"
    def dig(src, dst):
        dist, prev, heap = {src: 0}, {}, [(0, src)]
        while heap:
            d, (x, y) = heapq.heappop(heap)
            if (x, y) == dst:
                break
            if d > dist[(x, y)]:
                continue
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 1 <= n[0] < w - 1 and 1 <= n[1] < h - 1 and land[n[1]][n[0]] != "W":
                    nd = d + (1 if land[n[1]][n[0]] in walk else 6)
                    if nd < dist.get(n, 1 << 30):
                        dist[n], prev[n] = nd, (x, y)
                        heapq.heappush(heap, (nd, n))
        assert dst in dist, f"{title}: the base at {dst} cannot be reached from the marine base at {src}"
        cell = dst
        while cell != src:
            if land[cell[1]][cell[0]] == "R":
                land[cell[1]][cell[0]] = "D"
            cell = prev[cell]

    for target in [spawn_x] + extra_spawn:
        dig(spawn_m, target)
    codes = {"G": GRASS, "D": DIRT, "F": FORD, "W": WATER, "R": ROCK}
    def on_foot(blocked):
        """The cells the marine base reaches on foot, going round the blocked ones."""
        seen, queue = {spawn_m}, [spawn_m]
        while queue:
            cx, cy = queue.pop()
            for n in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if n not in seen and 1 <= n[0] < w - 1 and 1 <= n[1] < h - 1 and land[n[1]][n[0]] in walk and n not in blocked:
                    seen.add(n)
                    queue.append(n)
        return seen

    # The objects standing on the map (Neutral actors). Blocking ones stay clear of the bases, and when they would still cut the two bases apart
    # (the match could never be won) none of them blocks.
    extra = []
    if objects:
        near = [(x, y) for _, _, x, y, _ in actors + xeno_actors]
        placed = [(n, x, y) for n, x, y in objects if 1 <= x < w - 1 and 1 <= y < h - 1]
        placed = [(open_variant(n) if any(abs(x - bx) < 8 and abs(y - by) < 8 for bx, by in near) else n, x, y) for n, x, y in placed]
        seen = on_foot({(x, y) for n, x, y in placed if open_variant(n) != n})
        if any(s not in seen for s in [spawn_x] + extra_spawn):
            print(f"{title}: blocking objects would cut the bases apart, so none of them blocks")
            placed = [(open_variant(n), x, y) for n, x, y in placed]
        extra = [(n, "Neutral", x, y, 0) for n, x, y in placed]
    # The ore fields (TGMC's ore drills): one per drill on walkable ground, kept clear of the bases (see mapobjects.yaml).
    ore = [(x, y) for x, y in fields
           if 1 <= x < w - 1 and 1 <= y < h - 1 and land[y][x] in "GDF"
           and not any(abs(x - bx) < 4 and abs(y - by) < 4 for _, _, bx, by, _ in actors + xeno_actors)
           and not any(abs(x - bx) < 4 and abs(y - by) < 4 for bx, by in extra_spawn)]
    # A field is worth nothing unless an engineer can walk up to it: keep those with a cell beside them that the marine
    # base reaches on foot. The rest (sealed rooms, drills behind TGMC's walls) are dropped. Objects in the way do not count:
    # every blocking one can be shot to pieces.
    if ore:
        reach = on_foot(set(ore))
        kept = [(x, y) for x, y in ore if any(n in reach for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))]
        # Any slot may be a marine, so every base gets a field within 40 cells: where TGMC put none, one goes on the
        # nearest open cell 6 or more cells from the base.
        added = 0
        for bx, by in [spawn_m, spawn_x] + extra_spawn:
            if any(abs(x - bx) + abs(y - by) <= 40 for x, y in kept):
                continue
            spots = sorted((abs(x - bx) + abs(y - by), x, y) for x, y in reach
                           if max(abs(x - bx), abs(y - by)) >= 6 and (x, y) not in kept
                           and all(n in reach for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))))
            if spots:
                kept.append(spots[0][1:])
                added += 1
        print(f"{title}: {len(kept)} ore fields, {len(ore) + added - len(kept)} unreachable dropped, {added} added beside a base")
        ore = kept
    extra += [("miner-field", "Neutral", x, y, 0) for x, y in ore]
    extra += [("platinum-vein", "Neutral", x, y, 0) for x, y in ore if (x, y) in set(platinum)]
    # TGMC's geothermal generators (geothermal-field, a capture point that lights the colony once repaired), where the marines can walk up.
    reach_all = on_foot(set())
    busy = {(x, y) for _, _, x, y, _ in extra}
    gens = [(x, y) for x, y in generators if (x, y) not in busy and any(n in reach_all for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
            and not any(abs(x - bx) < 4 and abs(y - by) < 4 for bx, by in [spawn_m, spawn_x] + extra_spawn)]
    extra += [("geothermal-field", "Neutral", x, y, 0) for x, y in gens]
    extra += distress_objective(reach_all, nukes, towers, [spawn_m, spawn_x] + extra_spawn, {(x, y) for _, _, x, y, _ in extra})
    original = rows
    def dug_art(x, y):
        """A tunnel cell dug through rock wears the picture of the nearest ordinary ground cell, not the repo's flat dirt tile."""
        for r in range(1, 8):
            for dx in range(-r, r + 1):
                for dy in (-r, r) if abs(dx) != r else range(-r, r + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and land[ny][nx] == original[ny][nx] and land[ny][nx] in "GD":
                        return art(nx, ny)
        return codes[land[y][x]]
    ground = (lambda x, y: (art(x, y) if land[y][x] == original[y][x] else dug_art(x, y), 0)) if art else (lambda x, y: (codes[land[y][x]], 0))
    if mission:
        # A campaign mission (CAMPAIGN below): the player's marines against the hive's bot, with the mission's objective and night set.
        rules = camo_rules(camo, weather) + f"\t\tObjectiveDefault: {mission['objective']}\n" + ("\t\tNightDefault: true\n" if mission.get("night") else "")
        write_map(folder, mission["title"], w, h, actors + xeno_actors + extra, "MissionSelector", [spawn_m, spawn_x], ground=ground,
                  extra_rules=rules, category="Campaign", xeno_bot="skirmish", brief=mission["brief"])
        return
    if ai_test:
        # An AI-vs-AI copy of the map for tuning the bots on it (see scenarios/test-aimap.lua).
        write_map(folder, title, w, h, actors + xeno_actors + extra, "MissionSelector", [spawn_m, spawn_x], scripts=("test-aimap",), ground=ground, extra_rules=camo_rules(camo, weather),
                  category="Conquest", marine_bot="skirmish", xeno_bot="skirmish", fast=True, drop_conquest=False)
        return
    write_map(folder, title, w, h, actors + xeno_actors + extra, "Lobby", [spawn_m, spawn_x] + extra_spawn, ground=ground, extra_rules=camo_rules(camo, weather),
              category="Conquest, Full size" if bases == 4 else "Conquest, Small",  # the map picker's filter tabs
              faction_start=True, players=FOUR_PLAYERS if bases == 4 else None,
              brief="TGMC's own map at full size, with its floors and walls." if bases == 4 else "TGMC's own map, shrunk for a quick match.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dev-maps", help="where the scenario, AI-test and screenshot maps go (default: build/dev-maps next to the mod folder's build): they stay out of the game's menus")
    ap.add_argument("--tgmc", help="a TGMC checkout; with it the maps converted from TGMC's own (tgmc_dmm.MAPS) are written too")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    dev_maps = args.dev_maps or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(args.out))), "dev-maps")
    os.makedirs(dev_maps, exist_ok=True)
    write_palette(os.path.join(args.out, "tgmc.pal"))
    write_cursor(os.path.join(args.out, "cursor.png"))
    write_clock(os.path.join(args.out, "clock.png"))
    write_shroud_tiles(args.out, tile=32)
    write_rally_marker(args.out)
    write_move_flash(args.out)
    write_hive_icon(args.out)
    write_pod_icon(args.out)
    write_support_icons(args.out)
    # The power list is the tall column on the left: its icons (and clock) are a quarter smaller than the production icons.
    for name in ("hive-icon", "pod-icon", "support-icon"):
        shrink_sheet(args.out, name + ".png", name + ".png")
    shrink_sheet(args.out, "clock.png", "small-clock.png")
    write_lights(args.out)
    write_shockwave(args.out)
    write_overlay(args.out)
    write_acid_pool(args.out)
    write_ability_props(args.out)
    write_repair_fx(args.out)
    write_rank_chevrons(args.out)
    write_miner_art(args.out)
    if args.tgmc:
        write_tgmc_miner_art(args.out, args.tgmc)
    write_miner_upgrade_icons(args.out)
    write_badge_upgrade_icons(args.out)
    write_map(os.path.join(args.out, "maps", "test-field"), "TGMC test field", 24, 24, TEST_FIELD, "Lobby", [(10, 12), (14, 12)])
    # The menu's backdrop: Landing Zone with a bot on each side, so the Alamo lands, the squad walks out and a fight follows.
    write_map(os.path.join(args.out, "maps", "shell-landing"), "Landing (menu backdrop)", 56, 36, [], "Shellmap",
              [(28, 26), (51, 7)], scripts=("shell-landing",), ground=shell_ground, faction_start=True,
              marine_bot="skirmish", xeno_bot="skirmish", extra_rules="World:\n\tShellmapRestart:\n")
    # TGMC's floor and wall pictures, for the full-size converted maps (a cell of a shrunk one is several TGMC tiles) and, by theme,
    # for the built maps.
    full = [n for n, spec in tgmc_dmm.MAPS.items() if spec["factor"] == 1]
    tiles = build_maptiles.prepare(args.tgmc, args.out, full) if args.tgmc else None
    for name, m in SKIRMISH_MAPS.items():
        w, h = m["size"]
        spawns = m["spawns"]
        ground, extra = built_map(name, m, tiles)
        bases = _base_actors(spawns)
        for _, _, x, y, _ in bases:
            assert 2 <= x <= w - 3 and 2 <= y <= h - 3 and m["ground"](x, y)[0] in (GRASS, DIRT), f"{name}: actor at {x},{y} is off the map or not on open ground"
        rules = camo_rules(THEME_CAMO[m["theme"]], m["weather"]) + ("\t\tNightDefault: true\n" if m.get("night") else "")
        four = len(spawns) == 4
        write_map(os.path.join(args.out, "maps", name), m["title"], w, h, bases + extra, "Lobby", spawns, ground=ground,
                  category="Conquest, Full size" if four else "Conquest, Small", faction_start=True, players=FOUR_PLAYERS if four else None,
                  extra_rules=rules, brief=m["brief"] + " Blasts breach its walls.")
        # An AI-vs-AI copy for tuning the bots on the map (see scenarios/test-aimap.lua); it stays out of the game's menus.
        write_map(os.path.join(dev_maps, "aimap-" + name), "AI test " + m["title"], w, h, bases + extra, "MissionSelector", spawns[:2],
                  scripts=("test-aimap",), ground=ground, category="Conquest", marine_bot="skirmish", xeno_bot="skirmish", fast=True, extra_rules=rules)
    if args.tgmc:
        # Operation Hot Drop: three missions on TGMC's own maps, in order, each with one of TGMC's game modes. The engine keeps
        # nothing from one map to the next, so nothing carries over: each mission starts from its own landing.
        for key, mission in CAMPAIGN.items():
            spec = tgmc_dmm.MAPS[mission["map"]]
            write_tgmc_map(os.path.join(args.out, "maps", key), mission["title"], *tgmc_dmm.load(args.tgmc, spec),
                           art=tiles.art(mission["map"]) if mission["map"] in full else None,
                           objects=tiles.actors.get(mission["map"]) if mission["map"] in full else None, open_variant=tiles.open_variant,
                           fields=ore_fields(args.tgmc, spec), platinum=ore_fields(args.tgmc, spec, "/obj/machinery/miner/damaged/platinum"),
                           camo=tgmc_dmm.CAMO.get(mission["map"].removesuffix("-full"), ""),
                           nukes=ore_fields(args.tgmc, spec, "/obj/effect/landmark/nuke_spawn"), towers=ore_fields(args.tgmc, spec, "/obj/effect/landmark/sensor_tower"),
                           generators=ore_fields(args.tgmc, spec, "/obj/machinery/power/geothermal"),
                           weather=tgmc_dmm.WEATHER.get(mission["map"].removesuffix("-full")), mission=mission)
        for name, spec in tgmc_dmm.MAPS.items():
            write_tgmc_map(os.path.join(args.out, "maps", name), spec["title"], *tgmc_dmm.load(args.tgmc, spec),
                           art=tiles.art(name) if name in full else None,
                           objects=tiles.actors.get(name) if name in full else None, open_variant=tiles.open_variant,
                           fields=ore_fields(args.tgmc, spec), platinum=ore_fields(args.tgmc, spec, "/obj/machinery/miner/damaged/platinum"), bases=4 if name in full else 2, camo=tgmc_dmm.CAMO.get(name.removesuffix("-full"), ""),
                           nukes=ore_fields(args.tgmc, spec, "/obj/effect/landmark/nuke_spawn"), towers=ore_fields(args.tgmc, spec, "/obj/effect/landmark/sensor_tower"),
                           generators=ore_fields(args.tgmc, spec, "/obj/machinery/power/geothermal"),
                           weather=tgmc_dmm.WEATHER.get(name.removesuffix("-full")))
            if name in full:
                write_tgmc_map(os.path.join(dev_maps, "aimap-" + name), "AI test " + spec["title"], *tgmc_dmm.load(args.tgmc, spec),
                               art=tiles.art(name), objects=tiles.actors.get(name), open_variant=tiles.open_variant, ai_test=True,
                               fields=ore_fields(args.tgmc, spec), platinum=ore_fields(args.tgmc, spec, "/obj/machinery/miner/damaged/platinum"), camo=tgmc_dmm.CAMO.get(name.removesuffix("-full"), ""),
                               nukes=ore_fields(args.tgmc, spec, "/obj/effect/landmark/nuke_spawn"), towers=ore_fields(args.tgmc, spec, "/obj/effect/landmark/sensor_tower"),
                           generators=ore_fields(args.tgmc, spec, "/obj/machinery/power/geothermal"),
                           weather=tgmc_dmm.WEATHER.get(name.removesuffix("-full")))
    for name, sc in SCENARIOS.items():
        width, height = sc.get("size", (24, 24))
        # "prop:<name>" is a built-map prop (a mapobj-<n> actor); without a TGMC checkout there are none and it is left out.
        if sc["actors"] == "sweep":
            sc["actors"] = sweep_actors()
        placed = [((tiles.props[a[0][5:]],) + a[1:] if a[0].startswith("prop:") else a) for a in sc["actors"] if tiles or not a[0].startswith("prop:")]
        write_map(os.path.join(dev_maps, name), name, width, height, placed, "MissionSelector",
                  sc.get("spawns", [(10, 8), (19, 17)]), scripts=sc["scripts"],
                  drop_conquest=sc.get("drop_conquest", False), xeno_bot=sc.get("xeno_bot"),
                  marine_bot=sc.get("marine_bot"), fast=sc.get("fast", True),
                  extra_rules=sc.get("extra_rules", ""),
                  human_faction=sc.get("human_faction", "marines"),
                  ground={"landing_zone": landing_zone_ground, "walls": walls_ground, "doorline": doorline_ground, "evac": evac_ground}.get(sc.get("ground"), flat_ground))
    write_map(os.path.join(args.out, "maps", "hold-the-line"), "Hold the Line", 40, 28, HOLD_THE_LINE, "Lobby, MissionSelector",
              [(6, 14), (33, 13)], scripts=("wave-survival",), ground=landing_zone_ground, category="Survival",
              drop_conquest=True, music=True)
    write_map(os.path.join(args.out, "maps", "night-raid"), "Night Raid", 40, 28, HOLD_THE_LINE, "Lobby, MissionSelector",
              [(6, 14), (33, 13)], scripts=("wave-survival", "mission-raid"), ground=landing_zone_ground, category="Survival",
              drop_conquest=True, music=True)
    write_map(os.path.join(args.out, "maps", "last-stand"), "Last Stand", 40, 28, HOLD_THE_LINE, "Lobby, MissionSelector",
              [(6, 14), (33, 13)], scripts=("wave-survival", "mission-last-stand"), ground=landing_zone_ground, category="Survival",
              drop_conquest=True, music=True)
    write_map(os.path.join(args.out, "maps", "the-hundred"), "The Hundred", 40, 28, HOLD_THE_LINE, "Lobby, MissionSelector",
              [(6, 14), (33, 13)], scripts=("wave-survival", "mission-hundred"), ground=landing_zone_ground, category="Survival",
              drop_conquest=True, music=True)
    write_map(os.path.join(args.out, "maps", "evac"), "Evac", 64, 48, EVAC, "Lobby, MissionSelector",
              [(7, 24), (62, 46)], scripts=("mission-evac",), ground=evac_ground, category="Survival",
              drop_conquest=True, music=True, extra_rules=EVAC_RULES)
    print(f"placeholders written to {args.out}")


if __name__ == "__main__":
    main()
