"""Generate the non-TGMC pieces the mod needs to load and show a test field.

Nothing here is TGMC art. It writes:
  tgmc.pal                      a flat grey 256-colour palette (OpenRA needs one for its palette setup)
  cursor.png                    the cursors: an arrow, and a drawn marker for move, attack, heal, repair, ability and deploy
  shroud.png, fog.png           14 edge tiles each for unexplored and out-of-sight cells; shroudfull.png and fogfull.png
  rally-flag.png, rally-circles.png  the rally point marker: a waving flag and pulsing ground rings
  rank-pips.png                      one, two and three amber chevrons under a promoted unit
  team-ring-N.png, team-plate-WxH.png indexed sprites in the player-colour range: a ring under each unit, a plate on each structure
  fx-fire.png, rubble-WxH.png        flames over a nearly dead structure, and the heap it leaves behind
  icon.png, flare.png, overlay.png   support power icons, the light a Flare leaves, and the aiming tint
  wounds.png                         blood splotches drawn over a hurt marine: frame 0 for half health, 1 for a quarter, 2 for critical
  clock.png                     production-icon clock overlay frames (62x46, a dark wedge that sweeps away)
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

CLOCK_W, CLOCK_H, CLOCK_FRAMES, CLOCK_COLS = 62, 46, 30, 6  # matches the sidebar palette's IconSize
# Template ids in tilesets/ground.yaml. Grass lists two images, which the engine picks between per cell. The byte
# after the id in map.bin is the tile's index within a multi-cell template, so it is 0 for every one of these.
GRASS, WATER, FORD, DIRT = 1, 2, 3, 4

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


def palette_entries():
    """A plain grey ramp. Only the palette-based paths read it; the TGMC-free tiles and sprites are RGBA.

    Entries 80-95 are the player-colour remap range (rules/palettes.yaml): the remap keeps each entry's brightness, so
    they run bright, 160 to 255, to give the team rings and plates a vivid owner colour."""
    ramp = [(160 + 6 * (i - 80),) * 3 for i in range(80, 96)]
    return [(i, i, i) for i in range(80)] + ramp + [(i, i, i) for i in range(96, 256)]


def write_palette(path):
    with open(path, "wb") as f:
        f.write(bytes(c for rgb in palette_entries() for c in rgb))


# One 32x32 cell per cursor, in the order tgmc/cursors.yaml lists them (its Start numbers are the indices here).
# Each is (name, hotspot x, hotspot y). Action cursors are centred on their target; the arrow points from its corner.
CURSORS = [
    ("default", 0, 0), ("move", 16, 16), ("move-blocked", 16, 16), ("attackmove", 16, 16), ("attackmove-blocked", 16, 16),
    ("assaultmove", 16, 16), ("assaultmove-blocked", 16, 16), ("attack", 16, 16), ("attackoutsiderange", 16, 16),
    ("heal", 16, 16), ("heal-blocked", 16, 16), ("repair", 16, 16), ("repair-blocked", 16, 16), ("ability", 16, 16),
    ("deploy", 16, 16), ("deploy-blocked", 16, 16), ("generic-blocked", 16, 16),
]
GREEN, RED, AMBER, GREY, BLUE, WHITE = (88, 214, 96), (232, 64, 56), (255, 190, 48), (150, 150, 150), (90, 170, 255), (240, 240, 240)


def _cursor_cell(name):
    """Draw one cursor on a 32x32 transparent cell. Every mark is drawn twice, a dark wide stroke then the colour, so it
    reads on grass, dirt and water alike. No TGMC art."""
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    dark = (0, 0, 0, 255)

    def line(pts, col, w=2):
        d.line(pts, fill=dark, width=w + 2)
        d.line(pts, fill=col + (255,), width=w)

    def ring(r, col, w=2, cx=16, cy=16):
        d.ellipse([cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1], outline=dark, width=w + 2)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col + (255,), width=w)

    def slash(col=RED):
        line([(7, 7), (25, 25)], col, 3)

    if name == "default":
        pts = [(1, 1), (1, 21), (7, 16), (12, 25), (15, 23), (10, 14), (18, 14)]
        d.polygon(pts, fill=dark)
        d.polygon([(2, 3), (2, 18), (7, 14), (13, 23), (14, 22), (9, 12), (16, 12)], fill=WHITE + (255,))
    elif name.startswith("move"):
        ring(9, GREEN); line([(16, 7), (16, 25)], GREEN); line([(7, 16), (25, 16)], GREEN)
    elif name.startswith("attackmove"):
        ring(9, AMBER); line([(16, 3), (16, 11)], AMBER); line([(16, 21), (16, 29)], AMBER)
        line([(3, 16), (11, 16)], AMBER); line([(21, 16), (29, 16)], AMBER)
    elif name.startswith("assaultmove"):
        ring(9, RED); line([(16, 9), (16, 23)], RED); line([(9, 16), (23, 16)], RED); ring(2, RED, 1)
    elif name == "attack":
        ring(8, RED); line([(16, 2), (16, 11)], RED); line([(16, 21), (16, 30)], RED)
        line([(2, 16), (11, 16)], RED); line([(21, 16), (30, 16)], RED)
    elif name == "attackoutsiderange":
        ring(8, (190, 110, 100), 1); line([(16, 2), (16, 8)], (190, 110, 100)); line([(16, 24), (16, 30)], (190, 110, 100))
        line([(2, 16), (8, 16)], (190, 110, 100)); line([(24, 16), (30, 16)], (190, 110, 100))
    elif name.startswith("heal"):
        col = GREEN if name == "heal" else GREY
        ring(10, WHITE if name == "heal" else GREY, 1); line([(16, 9), (16, 23)], col, 4); line([(9, 16), (23, 16)], col, 4)
    elif name.startswith("repair"):
        col = AMBER if name == "repair" else GREY
        line([(8, 24), (20, 12)], col, 4); ring(5, col, 2, 22, 10)
    elif name == "ability":
        ring(10, BLUE); line([(16, 6), (16, 26)], BLUE); line([(6, 16), (26, 16)], BLUE); ring(3, WHITE, 1)
    elif name == "generic-blocked":
        ring(10, GREY); slash()
    elif name.startswith("deploy"):
        col = BLUE if name == "deploy" else GREY
        ring(10, col); line([(16, 8), (16, 23)], col, 3); line([(10, 17), (16, 24), (22, 17)], col, 3)
    if name.endswith("-blocked"):
        slash()
    return img


def write_cursor(path):
    """The cursor sheet, drawn here so the mod has cursors without any TGMC art: one cell per entry of CURSORS."""
    sheet = Image.new("RGBA", (32 * len(CURSORS), 32), (0, 0, 0, 0))
    for i, (name, _, _) in enumerate(CURSORS):
        sheet.paste(_cursor_cell(name), (32 * i, 0))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", "32,32")
    meta.add_text("FrameAmount", str(len(CURSORS)))
    sheet.save(path, pnginfo=meta)


def write_shroud_tiles(out, tile=32):
    """Edge tiles for ShroudRenderer. Frame i - 1 darkens the quadrants named by the bits of i (1 TL, 2 TR, 4 BR, 8 BL)."""
    half = tile // 2
    quadrants = {1: (0, 0), 2: (half, 0), 4: (half, half), 8: (0, half)}
    for name, alpha in (("shroud", 255), ("fog", 128)):
        sheet = Image.new("RGBA", (tile * 14, tile), (0, 0, 0, 0))
        for pattern in range(1, 15):
            for bit, (x, y) in quadrants.items():
                if pattern & bit:
                    sheet.paste((0, 0, 0, alpha), (tile * (pattern - 1) + x, y, tile * (pattern - 1) + x + half, y + half))
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


TEAM_LO, TEAM_HI = 82, 95  # palette indices in the player-colour remap range; the ring is shaded between them


def write_team_markers(out):
    """Indexed sprites painted with the player-colour range, so the engine recolours them per owner (the TGMC unit
    sprites are RGBA and cannot be recoloured). `team-ring-N.png` is an ellipse under a unit's feet in an NxN cell;
    `team-plate-WxH.png` is a short bar along the bottom of a WxH structure cell."""
    def sheet(size, draw):
        img = Image.new("P", size, 0)
        img.putpalette([c for rgb in palette_entries() for c in rgb])
        draw(ImageDraw.Draw(img))
        return img

    def save(img, name):
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", f"{img.width},{img.height}")
        meta.add_text("FrameAmount", "1")
        img.save(os.path.join(out, name), pnginfo=meta, optimize=False)

    for cell, feet, rx, ry in ((32, 29, 9, 3), (48, 44, 12, 4), (64, 59, 16, 5)):
        def draw(d, cell=cell, feet=feet, rx=rx, ry=ry):
            box = [cell // 2 - rx, feet - ry, cell // 2 + rx, feet + ry]
            d.ellipse([box[0] - 1, box[1] - 1, box[2] + 1, box[3] + 1], outline=2, width=1)
            d.ellipse(box, outline=TEAM_HI, width=2 if cell > 32 else 1)
        save(sheet((cell, cell), draw), f"team-ring-{cell}.png")

    # A plate sits along the bottom of the structure's footprint, so each footprint has its own cell size
    for w, h in ((32, 32), (64, 64), (96, 96), (32, 64)):
        def plate(d, w=w, h=h):
            x0, x1, y1 = w // 2 - min(w // 2 - 3, 12), w // 2 + min(w // 2 - 3, 12), h - 3
            d.rectangle([x0 - 1, y1 - 6, x1 + 1, y1 + 0], fill=2)
            d.rectangle([x0, y1 - 5, x1, y1 - 1], fill=TEAM_HI)
            d.rectangle([x0, y1 - 5, x1, y1 - 4], fill=TEAM_HI - 2)
            d.rectangle([x0, y1 - 2, x1, y1 - 1], fill=TEAM_LO)
        save(sheet((w, h), plate), f"team-plate-{w}x{h}.png")


def write_ruin_art(out):
    """`fx-fire.png`: four 24x32 frames of flames, drawn here, that flicker over a badly damaged structure.
    `rubble-WxH.png`: a scorched heap of broken blocks for each structure footprint, left where a structure dies."""
    import random
    rnd = random.Random(7)

    def save(img, name, frames):
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", f"{img.width // frames},{img.height}")
        meta.add_text("FrameAmount", str(frames))
        img.save(os.path.join(out, name), pnginfo=meta)

    flames = Image.new("RGBA", (24 * 4, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(flames)
    for i in range(4):
        for k, (bx, h) in enumerate(((6, 20), (12, 26), (18, 18))):
            x, hh = 24 * i + bx, h + rnd.randint(-4, 3)
            for col, scale in (((196, 40, 12, 230), 1.0), ((255, 150, 24, 240), 0.72), ((255, 232, 120, 250), 0.42)):
                ht, wd = hh * scale, 6 * scale + 1
                d.polygon([(x - wd, 31), (x - wd * 0.4 + rnd.randint(-1, 1), 31 - ht * 0.6), (x + rnd.randint(-1, 1), 31 - ht),
                           (x + wd * 0.4, 31 - ht * 0.6), (x + wd, 31)], fill=col)
    save(flames, "fx-fire.png", 4)

    for w, h in ((32, 32), (64, 64), (96, 96)):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # a dark scorch mark, then broken blocks of varied size heaped toward the middle
        d.ellipse([w * 0.1, h * 0.25, w * 0.9, h * 0.95], fill=(18, 16, 14, 190))
        for _ in range(int(w * h / 90)):
            cx = w / 2 + rnd.gauss(0, w * 0.2)
            cy = h * 0.62 + rnd.gauss(0, h * 0.14)
            bw, bh = rnd.randint(2, max(3, w // 9)), rnd.randint(2, max(3, h // 12))
            shade = rnd.randint(46, 104)
            d.rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], fill=(shade, shade - 4, shade - 8, 255),
                        outline=(20, 18, 16, 255))
        save(img, f"rubble-{w}x{h}.png", 1)


def write_ability_art(out):
    """`icon.png`: the 62x46 icons of the support powers (Screech, Flare, Orbital Strike). `flare.png`: four 48x48 frames of the light a
    Flare leaves on the ground. Drawn here, no TGMC art."""
    icons = Image.new("RGBA", (62 * 3, 46), (0, 0, 0, 0))
    for i in range(3):
        cell = Image.new("RGBA", (62, 46), (22, 28, 24, 255))
        d = ImageDraw.Draw(cell)
        d.rectangle([0, 0, 61, 45], outline=(88, 100, 70, 255))
        if i == 0:  # Screech: a mouth of sound waves
            for r, a in ((6, 255), (12, 200), (18, 140), (24, 90)):
                d.arc([31 - r, 23 - r, 31 + r, 23 + r], 300, 60, fill=(190, 90, 255, a), width=3)
                d.arc([31 - r, 23 - r, 31 + r, 23 + r], 120, 240, fill=(190, 90, 255, a), width=3)
            d.ellipse([27, 19, 35, 27], fill=(235, 200, 255, 255))
        elif i == 2:  # Orbital strike: a target ring with a beam coming down
            d.ellipse([16, 24, 46, 40], outline=(255, 90, 60, 255), width=2)
            d.line([(31, 2), (31, 32)], fill=(255, 220, 200, 255), width=3)
            d.ellipse([27, 28, 35, 36], fill=(255, 140, 60, 255))
        else:  # Flare: a bright star with a trail
            d.line([(14, 40), (31, 23)], fill=(150, 80, 20, 255), width=3)
            for ang in range(0, 360, 45):
                dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                length = 17 if ang % 90 == 0 else 11
                d.line([(33, 21), (33 + dx * length, 21 + dy * length)], fill=(255, 205, 80, 255), width=2)
            d.ellipse([27, 15, 39, 27], fill=(255, 245, 190, 255))
        icons.paste(cell, (62 * i, 0))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", "62,46")
    meta.add_text("FrameAmount", "3")
    icons.save(os.path.join(out, "icon.png"), pnginfo=meta)

    # The tint a support power puts on each cell it will affect while you aim it
    cell = Image.new("RGBA", (32, 32), (180, 90, 255, 60))
    ImageDraw.Draw(cell).rectangle([0, 0, 31, 31], outline=(210, 140, 255, 150))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", "32,32")
    meta.add_text("FrameAmount", "1")
    cell.save(os.path.join(out, "overlay.png"), pnginfo=meta)

    size = 48
    flare = Image.new("RGBA", (size * 4, size), (0, 0, 0, 0))
    for i in range(4):
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        px = glow.load()
        radius = 21 - (i % 2) * 2
        for y in range(size):
            for x in range(size):
                dist = math.hypot(x - size / 2, y - size / 2)
                if dist < radius:
                    t = 1 - dist / radius
                    px[x, y] = (255, int(150 + 100 * t), int(40 + 140 * t * t), int(190 * t + 40))
        flare.paste(glow, (size * i, 0))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{size},{size}")
    meta.add_text("FrameAmount", "4")
    flare.save(os.path.join(out, "flare.png"), pnginfo=meta)


def write_wounds(out):
    """Three 32x32 frames of blood on a marine's torso, arm and leg. Each frame has the last one's marks plus more, so
    the overlay for a worse state replaces the milder one. Drawn once, for the front view, whichever way the marine faces."""
    marks = [  # (cx, cy, radius) in a 32x32 cell, torso at about (16, 15)
        [(15, 14, 2), (19, 17, 1)],
        [(15, 14, 3), (19, 17, 2), (12, 20, 2), (18, 11, 1)],
        [(15, 14, 4), (19, 17, 3), (12, 20, 3), (18, 11, 2), (13, 25, 2), (21, 22, 2), (10, 14, 1)],
    ]
    sheet = Image.new("RGBA", (32 * len(marks), 32), (0, 0, 0, 0))
    for i, frame_marks in enumerate(marks):
        d = ImageDraw.Draw(sheet)
        for cx, cy, r in frame_marks:
            x = 32 * i + cx
            d.ellipse([x - r - 1, cy - r - 1, x + r + 1, cy + r + 1], fill=(70, 3, 5, 200))
            d.ellipse([x - r, cy - r, x + r, cy + r], fill=(150, 10, 10, 235))
            d.point([x - r // 2, cy - r // 2], fill=(220, 60, 50, 255))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", "32,32")
    meta.add_text("FrameAmount", str(len(marks)))
    sheet.save(os.path.join(out, "wounds.png"), pnginfo=meta)


def write_rank_pips(out):
    """Three 14x14 frames: one, two and three amber chevrons, drawn with a dark outline so they read on any terrain."""
    size = 14
    sheet = Image.new("RGBA", (size * 3, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for i in range(3):
        for k in range(i + 1):
            y = size - 4 - 3 * k
            chevron = [(size * i + 2, y), (size * i + 7, y - 3), (size * i + 12, y)]
            d.line(chevron, fill=(25, 18, 5, 255), width=3)
            d.line(chevron, fill=(255, 196, 51, 255), width=1)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{size},{size}")
    meta.add_text("FrameAmount", "3")
    sheet.save(os.path.join(out, "rank-pips.png"), pnginfo=meta)


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
    # A marine dies, leaves a corpse, and the corpse goes away again (see scenarios/test-death.lua)
    "scenario-death": _scenario("test-death", [
        ("rifleman", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 3, 3, 512),
    ]),
    # Marines at different health, ranks and one dying, to look at (mod/smoke.sh look-marines; scenarios/look-marines.lua)
    "look-marines": _scenario("look-marines", [("rifleman", "Marines", 6 + 2 * i, 10, 512) for i in range(5)]
                              + [("rifleman", "Marines", 6 + 2 * i, 13, 512) for i in range(4)]),
    # Everything on show, to look at (mod/smoke.sh look-all; scenarios/look-all.lua)
    "look-all": {"scripts": ("look-all",), "allied": True, "size": (40, 24), "spawns": [(4, 4), (30, 20)], "actors": (
        [(u, "Marines", 4 + 2 * i, 4, 512) for i, u in enumerate(["rifleman", "medic", "engineer", "smartgunner", "grenadier", "mortar-crew", "mech"])]
        + [(u, "Xenos", 4 + 2 * i, 7, 512) for i, u in enumerate(["runner", "hunter", "sentinel", "drone", "warrior", "queen", "crusher", "boiler"])]
        + [(u, "Marines", 5 + 3 * i, 11, 0) for i, u in enumerate(["vendor", "cryo-pod", "armory", "ordnance-depot", "mech-bay", "miner", "sentry-turret", "cade"])]
        + [(u, "Xenos", 5 + 4 * i, 15, 0) for i, u in enumerate(["weed-node", "resin-turret", "mini-silo", "evolution-tower", "maturity-tower", "resin-wall"])]
        + [("resin-silo", "Xenos", 30, 18, 0)])},
    # Ranks: a scripted promotion, and a runner that ranks up by killing (see scenarios/test-vet.lua). Spare marines keep the game going.
    "scenario-vet": _scenario("test-vet", [
        ("rifleman", "Marines", 10, 10, 512),
        ("rifleman", "Marines", 3, 3, 512),
        ("rifleman", "Marines", 4, 3, 512),
        ("runner", "Xenos", 12, 10, 0),
    ]),
    # A destroyed structure leaves rubble, which fades (see scenarios/test-ruin.lua)
    "scenario-ruin": _scenario("test-ruin", [
        ("armory", "Marines", 10, 10, 0),
        ("rifleman", "Marines", 3, 3, 512),
    ]),
    # Pounce, stealth, screech and flare, each against a control (see scenarios/test-abilities.lua)
    "scenario-abilities": {"scripts": ("test-abilities",), "size": (40, 30), "actors": [
        ("runner", "Xenos", 3, 3, 256), ("rifleman", "Marines", 8, 3, 768),
        ("rifleman", "Marines", 30, 14, 768),
        ("hunter", "Xenos", 16, 3, 256), ("rifleman", "Marines", 22, 3, 768),
        ("hunter", "Xenos", 16, 9, 256), ("rifleman", "Marines", 22, 9, 768),
        ("rifleman", "Marines", 3, 17, 256), ("rifleman", "Marines", 3, 20, 256),
        ("resin-silo", "Xenos", 34, 25, 0),
    ]},
    # Artillery shoots at range, not up close (see scenarios/test-artillery.lua)
    "scenario-artillery": {"scripts": ("test-artillery",), "size": (40, 28), "actors": [
        ("mortar-crew", "Marines", 3, 3, 768), ("runner", "Xenos", 9, 3, 256),
        ("mortar-crew", "Marines", 3, 10, 768), ("runner", "Xenos", 5, 10, 256),
        ("boiler", "Xenos", 25, 3, 768), ("rifleman", "Marines", 31, 3, 256),
        ("boiler", "Xenos", 25, 10, 768), ("rifleman", "Marines", 27, 10, 256),
        ("resin-silo", "Xenos", 34, 22, 0),
    ]},
    # Heavy armour: rifle fire against a Crusher and a Hunter, and a mech's cannon against a Crusher (see scenarios/test-armor.lua)
    "scenario-armor": {"scripts": ("test-armor",), "size": (40, 28), "actors": [
        ("rifleman", "Marines", 4, 3, 768), ("crusher", "Xenos", 8, 3, 256),
        ("rifleman", "Marines", 4, 10, 768), ("hunter", "Xenos", 8, 10, 256),
        ("mech", "Marines", 24, 3, 768), ("crusher", "Xenos", 28, 3, 256),
        ("resin-silo", "Xenos", 34, 22, 0),
    ]},
    # A Research Lab makes marines take less damage (see scenarios/test-research.lua), a Weed Node speeds xenos up
    # (test-weeds.lua), and the orbital strike marker blows up what is under it (test-orbital.lua)
    "scenario-research-off": {"scripts": ("test-research-off",), "size": (30, 20), "actors": [
        ("rifleman", "Marines", 8, 5, 768), ("crusher", "Xenos", 12, 5, 256), ("resin-silo", "Xenos", 24, 14, 0)]},
    "scenario-research-on": {"scripts": ("test-research-on",), "size": (30, 20), "actors": [
        ("rifleman", "Marines", 8, 5, 768), ("research-lab", "Marines", 3, 12, 0), ("crusher", "Xenos", 12, 5, 256),
        ("resin-silo", "Xenos", 24, 14, 0)]},
    "scenario-weeds": {"scripts": ("test-weeds",), "size": (40, 26), "actors": [
        ("weed-node", "Xenos", 4, 6, 0), ("runner", "Xenos", 5, 5, 256), ("runner", "Xenos", 5, 20, 256),
        ("rifleman", "Marines", 36, 22, 768)]},
    "scenario-orbital": {"scripts": ("test-orbital",), "size": (30, 24), "actors": [
        ("runner", "Xenos", 10, 10, 256), ("rifleman", "Marines", 18, 10, 768), ("resin-silo", "Xenos", 24, 18, 0)]},
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
    # The tech tree and the Miner and Weed Node income (see scenarios/test-build.lua). The xeno side has a queen and a silo.
    "scenario-build": {"scripts": ("test-build",), "actors": [
        ("engineer", "Marines", 10, 10, 512),
        ("cryo-pod", "Marines", 6, 6, 0),
        ("queen", "Xenos", 20, 16, 0),
        ("resin-silo", "Xenos", 16, 16, 0),
    ]},
    # The Skirmish AI at each strength spends its cash on units (see scenarios/test-ai-levels.lua)
    "scenario-ai-easy": {"scripts": ("test-ai-level-easy",), "xeno_bot": "easy", "size": (40, 28), "actors": [
        ("rifleman", "Marines", 3, 3, 512), ("resin-silo", "Xenos", 33, 21, 0)]},
    "scenario-ai-normal": {"scripts": ("test-ai-level-normal",), "xeno_bot": "skirmish", "size": (40, 28), "actors": [
        ("rifleman", "Marines", 3, 3, 512), ("resin-silo", "Xenos", 33, 21, 0)]},
    "scenario-ai-hard": {"scripts": ("test-ai-level-hard",), "xeno_bot": "hard", "size": (40, 28), "actors": [
        ("rifleman", "Marines", 3, 3, 512), ("resin-silo", "Xenos", 33, 21, 0)]},
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
                         "actors": HOLD_THE_LINE, "extra_rules": "Player:\n\t-SquadManagerBotModule@normal-marines:\n"},
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
              music=False, allied=False, preview=None):
    # `allied` makes the two sides friends, so a viewer sees both (the look-* maps). A scenario map has no slot for the xenos: they are a scripted player, so Lua can find them and they never act.
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
        here = os.path.dirname(os.path.abspath(__file__))
        # Scripts that are one template with a word filled in: the bot strength, or whether a Research Lab stands
        templates = (("test-ai-level-", "test-ai-levels.lua", "__LEVEL__"), ("test-research-", "test-research.lua", "__MODE__"))
        for name in scripts:
            if name == "sound-list":
                write_sound_list(os.path.join(folder, "sound-list.lua"))
                continue
            source = os.path.join(here, "scenarios", f"{name}.lua")
            text = None
            for prefix, template_name, token in templates:
                if name.startswith(prefix):
                    with open(os.path.join(here, "scenarios", template_name), encoding="utf-8") as f:
                        text = f.read().replace(token, name[len(prefix):])
            if text is None:
                shutil.copyfile(source, os.path.join(folder, f"{name}.lua"))
            else:
                with open(os.path.join(folder, f"{name}.lua"), "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)


    # An allied (look-*) map also pins the two colours, so a screenshot shows the owner colouring
    marine_rel = "\t\tAllies: Xenos\n\t\tLockColor: True\n" if allied else "\t\tEnemies: Xenos\n"
    xeno_rel = "\t\tAllies: Marines\n\t\tLockColor: True\n" if allied else "\t\tEnemies: Marines\n"
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
		Color: 3BA0FF
{marine_rel}		Spawn: 1
		LockSpawn: True
	PlayerReference@Xenos:
		Name: Xenos
		Playable: {not script}
{xeno_bot_line}		Faction: xenos
		LockFaction: True
		Color: FF4B3B
{xeno_rel}		Spawn: 2
		LockSpawn: True
{observer_block}
Actors:
{"".join(actors)}"""
    with open(os.path.join(folder, "map.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(yaml)

    if preview is None:
        preview = Image.new("RGBA", (size_w, size_h), (0x2E, 0x52, 0x30, 255))
    preview.save(os.path.join(folder, "map.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    write_palette(os.path.join(args.out, "tgmc.pal"))
    write_cursor(os.path.join(args.out, "cursor.png"))
    write_clock(os.path.join(args.out, "clock.png"))
    write_shroud_tiles(args.out, tile=32)
    write_rally_marker(args.out)
    write_team_markers(args.out)
    write_ruin_art(args.out)
    write_ability_art(args.out)
    write_wounds(args.out)
    write_rank_pips(args.out)
    write_map(os.path.join(args.out, "maps", "test-field"), "TGMC test field", 24, 24, TEST_FIELD, "Lobby, Shellmap", [(10, 12), (14, 12)])
    write_map(os.path.join(args.out, "maps", "landing-zone"), "Landing Zone", 40, 28, LANDING_ZONE, "Lobby", [(6, 14), (33, 13)],
              ground=landing_zone_ground, category="Conquest")
    for name, sc in SCENARIOS.items():
        width, height = sc.get("size", (24, 24))
        write_map(os.path.join(args.out, "maps", name), name, width, height, sc["actors"], "MissionSelector",
                  sc.get("spawns", [(10, 8), (19, 17)]), scripts=sc["scripts"],
                  drop_conquest=sc.get("drop_conquest", False), xeno_bot=sc.get("xeno_bot"),
                  marine_bot=sc.get("marine_bot"), fast=sc.get("fast", True),
                  extra_rules=sc.get("extra_rules", ""), allied=sc.get("allied", False),
                  ground=landing_zone_ground if sc.get("ground") == "landing_zone" else flat_ground)
    write_map(os.path.join(args.out, "maps", "hold-the-line"), "Hold the Line", 40, 28, HOLD_THE_LINE, "Lobby",
              [(6, 14), (33, 13)], scripts=("wave-survival",), ground=landing_zone_ground, category="Survival",
              drop_conquest=True, music=True)
    print(f"placeholders written to {args.out}")


if __name__ == "__main__":
    main()
