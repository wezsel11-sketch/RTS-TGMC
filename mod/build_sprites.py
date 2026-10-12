"""Build OpenRA sprite sheets and sequence YAML for the TGMC units in UNITS.

For each unit, each sequence is a stack of TGMC .dmi states (layers, composited
bottom to top). Each sequence is written facing-major into one PNG sheet per
unit:

  cell = facing * frames + frame        (OpenRA's Start/Length/Facings/Stride)

TGMC art has 4 directions (S, N, E, W). OpenRA wants 8 facings, ordered
clockwise from north: N, NE, E, SE, S, SW, W, NW. Diagonals borrow the
side sprite on their own horizontal side (NE/SE take E, SW/NW take W).
TGMC supplies both E and W, so nothing is mirrored; the Doom mod mirrors
because its sprites lack one side. 1-dir states get Facings: 1.

A layer may carry a fourth element, a dict of options, for effect art: "frames" (start, stop, step) keeps a slice of the
frames, "rotate" turns a 1-dir state by that many degrees clockwise, "facings" then makes that many rotated copies of
every frame (a muzzle flash or tracer that has to point along the shot), "swap_rg" swaps the red and green channels (the
green xeno splatter becomes red marine blood), "size" scales the frames to that many pixels
square, "fit" (w, h) shrinks them into a box of that size keeping the aspect ratio, "side" keeps one side (S, N, E, W) of a
4-direction state, and "tick" sets the milliseconds per frame. On the first layer of a sequence, "fade" (N) turns the composited still pose
into N frames that fade out. A unit may also carry "cell": (w, h), which centres every frame of its sheet on a cell that
size (a 32px marine sheet that has to hold TGMC's 64px gib frames).

Animation timing comes from the .dmi `delay` list (deciseconds per frame). OpenRA has one `Tick`
(ms per frame) per sequence, so Tick is the GCD of the delays and a frame that holds longer is
repeated in the sheet. A state with no delay list keeps OpenRA's default Tick.

Output (default build/mod/tgmc):
  sprites/<unit>.png     sheet; FrameSize and FrameAmount are PNG text chunks
  sequences/<unit>.yaml  OpenRA sequence definitions for the unit

Usage: build_sprites.py --tgmc CHECKOUT [--out DIR]
"""
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageChops, PngImagePlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgmc_dmi  # noqa: E402

HUMAN = "icons/mob/human.dmi"
MARINE_UNIFORM = "icons/mob/clothing/uniforms/marine_uniforms.dmi"
RUNNER = "icons/Xeno/castes/runner.dmi"
HUNTER = "icons/Xeno/castes/hunter.dmi"
SENTINEL = "icons/Xeno/castes/sentinel.dmi"
DRONE = "icons/Xeno/castes/drone.dmi"
ACID_TURRET = "icons/Xeno/acid_turret.dmi"
RESIN_SILO = "icons/Xeno/resin_silo.dmi"
RESIN_POD = "icons/Xeno/resin_pod.dmi"
SENTRY = "icons/obj/machines/deployable/sentry/sentry.dmi"
MARINE_ARMOR = "icons/mob/clothing/suits/marine_armor.dmi"
MARINE_HELMETS = "icons/mob/clothing/headwear/marine_helmets.dmi"
HUMAN_GIB = "icons/mob/human_gib.dmi"
FEET = "icons/mob/clothing/feet.dmi"
RIFLES = "icons/mob/inhands/guns/rifles_right_1.dmi"
SMGS = "icons/mob/inhands/guns/submachineguns_right_1.dmi"
PISTOLS = "icons/mob/inhands/guns/pistols_right_1.dmi"
CRYO = "icons/obj/machines/cryogenics2.dmi"
VENDING = "icons/obj/machines/vending.dmi"
WARRIOR = "icons/Xeno/castes/warrior.dmi"
GRENADE = "icons/obj/items/grenade.dmi"
PROJECTILES = "icons/obj/items/projectiles.dmi"
FX64 = "icons/effects/64x64.dmi"
FX96 = "icons/effects/96x96.dmi"
FX32 = "icons/effects/effects.dmi"
HEAVY_IMPACT = "icons/effects/heavyimpact.dmi"
XENO_FX = "icons/Xeno/Effects.dmi"
QUEEN = "icons/Xeno/castes/queen.dmi"
WEEDS = "icons/Xeno/weeds.dmi"
XENO_2X2 = "icons/Xeno/2x2building.dmi"
RESIN_WALL = "icons/obj/smooth_objects/resin-wall.dmi"
MINING_DRILL = "icons/obj/mining_drill.dmi"
CADE = "icons/obj/structures/barricades/metal.dmi"

# OpenRA facing order (clockwise from north) -> which TGMC side to draw.
FACING_NAMES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
FACING_SOURCE = {"N": "N", "NE": "E", "E": "E", "SE": "E", "S": "S", "SW": "W", "W": "W", "NW": "W"}

# unit -> sequence -> list of (dmi path, state name[, multiply tint]) layers, bottom first.
# A sequence given as a string reuses another sequence's cells (an alias, no new art).
# "name:S" aliases a single facing of that sequence (N, NE, E, SE, S, SW, W or NW), and "name#1" keeps every facing
# but only the first frame, which gives an animated walk a still pose to stand in.
# TGMC's standard marine kit, the unprefixed states, which are a mottled grey-brown pattern camo that shows up well
# against green terrain (the "m_" jungle set is dark and blends in). The boots go over the armour, whose legs would
# otherwise hide them.
GEAR = [(MARINE_ARMOR, "xarmor"), (FEET, "marine"), (MARINE_HELMETS, "helmet")]


def marine(uniform, weapon):
    """Body, role uniform, armour, boots and helmet, then the weapon held in the right hand."""
    return [(HUMAN, "body_m"), (MARINE_UNIFORM, uniform)] + GEAR + [weapon]


def marine_die(uniform, weapon):
    """The marine's pose, front on, fading out over 6 frames: the death animation for a kill that is not an explosion."""
    layers = [(HUMAN, "body_m"), (MARINE_UNIFORM, uniform)] + GEAR + [weapon]
    layers = [layer + (None, {"side": "S"}) for layer in layers]
    layers[0] = layers[0][:2] + (None, {"side": "S", "fade": 6, "tick": 70})
    return layers


# TGMC's human gib is 64px and the marine is 32px, so the marine sheets hold 64px cells.
MARINE_CELL = (64, 64)
MARINE_GIB = [(HUMAN_GIB, "default", None, {"tick": 70})]

UNITS = {
    "rifleman": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_jumpsuit", (RIFLES, "t18_w")),
            "die": marine_die("marine_jumpsuit", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "runner": {
        "sequences": {
            "stand": [(RUNNER, "Runner Walking")],
            "run": [(RUNNER, "Runner Running")],
            "die": [(RUNNER, "Runner Dead")],
            "die-gib": [(RUNNER, "gibbed-a-runner", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    # More xeno castes. Hunter and Sentinel have a real animated walk; Drone is a still pose.
    "hunter": {
        "sequences": {
            "walk": [(HUNTER, "Hunter Walking")],
            "run": [(HUNTER, "Hunter Running")],
            "stand": "walk#1",
            "die": [(HUNTER, "Hunter Dead")],
            "die-gib": [(HUNTER, "Hunter Gibbed", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "sentinel": {
        "sequences": {
            "walk": [(SENTINEL, "Sentinel Walking")],
            "run": [(SENTINEL, "Sentinel Running")],
            "stand": "walk#1",
            "die": [(SENTINEL, "Sentinel Dead")],
            "die-gib": [(SENTINEL, "gibbed-a-small", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "drone": {
        "sequences": {
            "stand": [(DRONE, "Drone Walking")],
            "run": [(DRONE, "Drone Running")],
            "die": [(DRONE, "Drone Dead")],
            "die-gib": [(DRONE, "gibbed-a-small", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "warrior": {
        "sequences": {
            "walk": [(WARRIOR, "Warrior Walking")],
            "run": [(WARRIOR, "Warrior Running")],
            "stand": "walk#1",
            "die": [(WARRIOR, "Warrior Dead")],
            "die-gib": "die",  # too heavy to gib: TGMC's bomb armour keeps it whole
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    # Marine roles. Same body as the rifleman, with the role's uniform state on top.
    "medic": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_medic", (PISTOLS, "m44")),
            "die": marine_die("marine_medic", (PISTOLS, "m44")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "engineer": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_engineer", (SMGS, "t19_w")),
            "die": marine_die("marine_engineer", (SMGS, "t19_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    # Marine gunners. Same kit as the other roles with their own uniform state; the weapon art is the rifle's.
    "smartgunner": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_assault_crewman", (RIFLES, "t18_w")),
            "die": marine_die("marine_assault_crewman", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 35})],
            "icon": "stand:S",
        },
    },
    "grenadier": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("pilot_spec", (RIFLES, "t18_w")),
            "die": marine_die("pilot_spec", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            # The grenade launcher's thump: a puff of dust at the muzzle, not a flash
            "flash": [(HEAVY_IMPACT, "heavyimpact", None, {"frames": (0, 9), "size": 32, "tick": 60})],
            "icon": "stand:S",
        },
    },
    # Marine structures. Sentry is 4-dir (8 facings). Cryo pod and vendor are 1-dir and animate in place.
    "sentry-turret": {
        "sequences": {
            "turret": [(SENTRY, "sentry_deployed")],
            "icon": [(SENTRY, "sentry_deployed", None, {"side": "S", "fit": (44, 44), "frames": (0, 1)})],
            "flash": [(PROJECTILES, "muzzle_flash", None, {"facings": 8, "tick": 50})],
        },
    },
    "cryo-pod": {
        "sequences": {
            "idle": [(CRYO, "cell_off")], "active": [(CRYO, "cell_on")],
            "icon": [(CRYO, "cell_off", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "vendor": {
        "sequences": {
            "idle": [(VENDING, "sustenance")],
            "icon": [(VENDING, "sustenance", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    # Xeno structures. Turret is 4-dir, so it gets 8 facings; silo and pod are 1-dir and animate in place.
    "resin-turret": {
        "sequences": {
            "turret": [(ACID_TURRET, "resin_turret")],
            "icon": [(ACID_TURRET, "resin_turret", None, {"side": "S", "fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "resin-silo": {
        "sequences": {
            "idle": [(RESIN_SILO, "weed_silo")],
            "icon": [(RESIN_SILO, "weed_silo", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "mini-silo": {
        "sequences": {
            "idle": [(RESIN_POD, "resinpod")],
            "icon": [(RESIN_POD, "resinpod", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    # Supply generators, walls and tech structures the players build. Each has a still "icon" for the Build menu, which
    # gets its own sheet scaled to fit the 62x46 palette cell.
    "queen": {
        "sequences": {
            "stand": [(QUEEN, "Queen Walking")],
            "run": [(QUEEN, "Queen Running")],
            "die": [(QUEEN, "Queen Dead")],
            "die-gib": "die",  # too heavy to gib: TGMC's bomb armour keeps it whole
            "attack": "stand",
            "icon": [(QUEEN, "Queen Walking", None, {"side": "S", "fit": (46, 46)})],
        },
    },
    "miner": {
        "sequences": {
            "idle": [(MINING_DRILL, "mining_drill_active_")],
            "icon": [(MINING_DRILL, "mining_drill_active_", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "cade": {
        "sequences": {
            "idle": [(CADE, "metal_0", None, {"side": "S"})],
            "icon": [(CADE, "metal_0", None, {"side": "S", "fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "armory": {
        "sequences": {
            "idle": [(VENDING, "marinearmory")],
            "icon": [(VENDING, "marinearmory", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "ordnance-depot": {
        "sequences": {
            "idle": [(VENDING, "robotics")],
            "icon": [(VENDING, "robotics", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "weed-node": {
        "sequences": {
            "idle": [(WEEDS, "weednode3")],
            "icon": [(WEEDS, "weednode3", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "resin-wall": {
        "sequences": {
            "idle": [(RESIN_WALL, "resin-wall-255")],
            "icon": [(RESIN_WALL, "resin-wall-255", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "evolution-tower": {
        "sequences": {
            "idle": [(XENO_2X2, "evotower")],
            "icon": [(XENO_2X2, "evotower", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "maturity-tower": {
        "sequences": {
            "idle": [(XENO_2X2, "maturitytower")],
            "icon": [(XENO_2X2, "maturitytower", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    # Projectile images. Weapons refer to these by name (Bullet Image:), not as actors.
    "grenade": {
        "sequences": {"idle": [(GRENADE, "grenade")]},
    },
    # Effect images, also named by weapons (Bullet Image, CreateEffect Image). One sheet per cell size.
    # The bullet art points up, so 16 turned copies make a tracer that flies along the shot.
    "fx-bullet": {
        "sequences": {
            "idle": [(PROJECTILES, "bullet", None, {"facings": 16})],
            "large": [(PROJECTILES, "bullet_large", None, {"facings": 16})],
        },
    },
    "fx-acid": {
        "sequences": {
            "idle": [(PROJECTILES, "xeno_acid", None, {"tick": 80})],
            "splash": [(XENO_FX, "acid_normal", None, {"tick": 60})],
            "sizzle": [(XENO_FX, "acid2", None, {"tick": 60})],
        },
    },
    "fx-impact": {
        "sequences": {
            "spark": [(PROJECTILES, "spark", None, {"tick": 60})],
            "blood": [(XENO_FX, "splatter", None, {"swap_rg": True, "tick": 70})],
            "gore": [(XENO_FX, "splatter", None, {"tick": 70})],
            "heal": [(FX32, "sparkle", None, {"tick": 60})],
            "burst": [(FX32, "explosion", None, {"tick": 40})],
        },
    },
    # The 65-frame TGMC explosions are a fireball that fades into smoke; every third frame at one tick each is about a second
    "fx-blast": {
        "sequences": {
            "grenade": [(FX64, "explosion", None, {"frames": (0, 65, 3), "tick": 40})],
            "small": [(FX64, "explosion", None, {"frames": (0, 40, 4), "tick": 40})],
        },
    },
    "fx-blast-big": {
        "sequences": {"big": [(FX96, "explosion", None, {"frames": (0, 65, 3), "tick": 40})]},
    },
    "fx-slam": {
        "sequences": {"slam": [(HEAVY_IMPACT, "heavyimpact", None, {"tick": 60})]},
    },
}


def tinted(img, rgb):
    """Multiply the colour channels by rgb/255 and keep the alpha."""
    if rgb is None:
        return img
    r, g, b, a = img.split()
    out = ImageChops.multiply(Image.merge("RGB", (r, g, b)), Image.new("RGB", img.size, rgb))
    out.putalpha(a)
    return out


def _layer_images(dmi, state, tint=None, opts=None):
    """Return {side: [frame images]} for S/N/E/W, {"*": [frame images]} for a 1-dir state, or, with the "facings"
    option, {0..facings-1: [frame images]} for a 1-dir state turned to each facing (facing 0 points north)."""
    opts = opts or {}
    frames = dmi.frames(state)
    if "frames" in opts:
        frames = frames[slice(*opts["frames"])]
    dirs = dmi.state(state)["dirs"]
    if dirs == 1 and "facings" in opts:
        count = opts["facings"]
        base = [tinted(fr[0], tint) for fr in frames]
        return {i: [img.rotate(-(opts.get("rotate", 0) + i * 360 / count), resample=Image.BICUBIC) for img in base]
                for i in range(count)}
    if dirs == 1:
        return {"*": [tinted(frames[f][0], tint).rotate(-opts.get("rotate", 0), resample=Image.BICUBIC)
                      for f in range(len(frames))]}
    if dirs != 4:
        raise SystemExit(f"{dmi.path}:{state} has {dirs} dirs; only 1 or 4 are handled")
    if "side" in opts:  # keep one side of a 4-direction state: a building that never turns
        d = tgmc_dmi.DIRS4.index(opts["side"])
        return {"*": [tinted(frames[f][d], tint) for f in range(len(frames))]}
    return {name: [tinted(frames[f][d], tint) for f in range(len(frames))] for d, name in enumerate(tgmc_dmi.DIRS4)}


def _swap_rg(img):
    r, g, b, a = img.split()
    return Image.merge("RGBA", (g, r, b, a))


def layer_images(dmi, state, tint=None, opts=None):
    sides = _layer_images(dmi, state, tint, opts)
    if (opts or {}).get("swap_rg"):
        sides = {k: [_swap_rg(img) for img in frames] for k, frames in sides.items()}
    size = (opts or {}).get("size")
    if size:
        sides = {k: [img.resize((size, size), Image.LANCZOS) for img in frames] for k, frames in sides.items()}
    fit = (opts or {}).get("fit")
    if fit:  # shrink to fit a (w, h) box, keeping the aspect ratio, centred on a transparent cell of that size
        def fitted(img):
            scale = min(fit[0] / img.width, fit[1] / img.height, 1.0)
            small = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
            cell = Image.new("RGBA", fit, (0, 0, 0, 0))
            cell.paste(small, ((fit[0] - small.width) // 2, (fit[1] - small.height) // 2))
            return cell
        sides = {k: [fitted(img) for img in frames] for k, frames in sides.items()}
    return sides


def composite(layers):
    """layers: list of (dmi, state, sides) -> {side or '*': [composited frames]}."""
    names = set(k for _, _, sides in layers for k in sides)
    out = {}
    for name in names:
        frame_count = len(layers[0][2][name])
        stacked = []
        for f in range(frame_count):
            base = None
            for dmi, state, sides in layers:
                img = sides[name][f]
                if base is None:
                    base = img.copy()
                else:
                    if img.size != base.size:
                        raise SystemExit(f"{dmi.path}:{state} is {img.size}, base is {base.size}")
                    base = Image.alpha_composite(base, img)
            stacked.append(base)
        out[name] = stacked
    return out


def fade_frames(img, count):
    """`count` copies of img whose alpha falls linearly: the first is untouched, the last is 1/count visible."""
    frames = []
    for i in range(count):
        r, g, b, a = img.convert("RGBA").split()
        frames.append(Image.merge("RGBA", (r, g, b, a.point(lambda v, i=i: round(v * (count - i) / count)))))
    return frames


def pad_to(img, size):
    """Centre img, unscaled, on a transparent cell of `size`."""
    if img.width > size[0] or img.height > size[1]:
        raise SystemExit(f"a {img.size} frame does not fit a {tuple(size)} cell")
    cell = Image.new("RGBA", tuple(size), (0, 0, 0, 0))
    cell.paste(img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2))
    return cell


def frame_timing(delays):
    """Map BYOND per-frame delays (deciseconds) to (tick_ms, frame indices to show), or (None, None).

    TGMC sometimes lists a delay of 0 for a frame, which BYOND treats as the shortest delay, so use 1.
    """
    if len(delays) < 2:
        return None, None
    delays = [max(1, d) for d in delays]
    unit = math.gcd(*delays)
    order = [i for i, d in enumerate(delays) for _ in range(d // unit)]
    return unit * 100, order


def render_sequences(tgmc, sequences, cell=None):
    """Composite every non-alias sequence in `sequences` into one list of cells. With `cell`, every frame is centred on a
    transparent cell of that size, so art of different sizes can share one sheet.

    Returns (cells, cell_size, seq_defs, aliases)."""
    sheet_cells = []      # PIL images, appended in cell order
    cell_size = None  # (width, height) of one cell
    seq_defs = []         # (sequence name, start, length, facings, tick or None, stride or None)
    aliases = []
    unit = ""
    for seq_name, layer_specs in sequences.items():
        if isinstance(layer_specs, str):
            aliases.append((seq_name, layer_specs))
            continue
        dmis = [(tgmc_dmi.Dmi(os.path.join(tgmc, spec[0])), spec[1]) for spec in layer_specs]
        layers = [(dmi, state, layer_images(dmi, state, spec[2] if len(spec) > 2 else None,
                                            spec[3] if len(spec) > 3 else None))
                  for (dmi, state), spec in zip(dmis, layer_specs)]
        sides = composite(layers)
        first_opts = layer_specs[0][3] if len(layer_specs[0]) > 3 else {}
        if "fade" in first_opts:  # a still pose that fades out over N frames
            sides = {k: fade_frames(frames[0], first_opts["fade"]) for k, frames in sides.items()}
        size = (dmis[0][0].icon_w, dmis[0][0].icon_h)
        if "size" in first_opts:
            size = (first_opts["size"], first_opts["size"])
        if "fit" in first_opts:
            size = tuple(first_opts["fit"])
        if cell:
            sides = {k: [pad_to(img, cell) for img in frames] for k, frames in sides.items()}
            size = tuple(cell)
        if cell_size is None:
            cell_size = size
        elif cell_size != size:
            raise SystemExit(f"{unit}: mixed icon sizes {cell_size} and {size}")

        if "*" in sides:
            sources = ["*"]
        elif 0 in sides:
            sources = sorted(sides)
        else:
            sources = [FACING_SOURCE[name] for name in FACING_NAMES]
        delays = dmis[0][0].state(dmis[0][1])["delays"]
        if "frames" in first_opts:
            delays = delays[slice(*first_opts["frames"])]
        tick, order = frame_timing(delays)
        if order is None or len(order) < len(sides[sources[0]]):
            tick, order = None, list(range(len(sides[sources[0]])))
        if "tick" in first_opts:
            tick = first_opts["tick"]
            order = list(range(len(sides[sources[0]])))
        start = len(sheet_cells)
        for source in sources:
            for f in order:
                sheet_cells.append(sides[source][f])
        seq_defs.append((seq_name, start, len(order), len(sources), tick, None))
    return sheet_cells, cell_size, seq_defs, aliases


def save_sheet(sheet_cells, cell_size, path):
    cols = 8
    rows = (len(sheet_cells) + cols - 1) // cols
    cw, ch = cell_size
    sheet = Image.new("RGBA", (cols * cw, rows * ch), (0, 0, 0, 0))
    for i, img in enumerate(sheet_cells):
        sheet.paste(img, ((i % cols) * cw, (i // cols) * ch))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{cw},{ch}")
    meta.add_text("FrameAmount", str(len(sheet_cells)))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet.save(path, pnginfo=meta)


def build_unit(tgmc, unit, spec, out_dir):
    # A real (non-alias) "icon" sequence goes on its own sheet, so a big structure can have a palette icon scaled down
    # to fit the 62x46 production cell without shrinking the sprite the map draws.
    icon_spec = spec["sequences"].get("icon")
    own_icon = icon_spec is not None and not isinstance(icon_spec, str)
    main = {k: v for k, v in spec["sequences"].items() if not (own_icon and k == "icon")}
    try:
        sheet_cells, cell_size, seq_defs, aliases = render_sequences(tgmc, main, spec.get("cell"))
    except SystemExit as e:
        raise SystemExit(f"{unit}: {e}")
    icon_cells = None
    if own_icon:
        icon_cells, icon_size, icon_defs, _ = render_sequences(tgmc, {"icon": icon_spec})

    starts = {name: (start, length, facings, tick, stride) for name, start, length, facings, tick, stride in seq_defs}
    for alias, target in aliases:  # an alias may point at an earlier alias, so resolve them in order
        target, _, still = target.partition("#")  # "walk#1" keeps every facing but shows only the first frame
        name, _, side = target.partition(":")
        start, length, facings, tick, stride = starts[name]
        if still:
            stride, length, tick = stride or length, int(still), None
        if side:  # "stand:S" is the one facing the icon should show, here the front
            if facings == 1:
                raise SystemExit(f"{unit}: {alias} wants side {side} of {name}, which has one facing")
            start += FACING_NAMES.index(side) * (stride or length)
            facings, stride = 1, None
        starts[alias] = (start, length, facings, tick, stride)
        seq_defs.append((alias, start, length, facings, tick, stride))

    cw, ch = cell_size
    os.makedirs(os.path.join(out_dir, "sequences"), exist_ok=True)
    save_sheet(sheet_cells, cell_size, os.path.join(out_dir, "sprites", f"{unit}.png"))
    if icon_cells is not None:
        save_sheet(icon_cells, icon_size, os.path.join(out_dir, "sprites", f"{unit}-icon.png"))

    lines = ["# Generated by mod/build_sprites.py from TGMC art. Do not edit.",
             f"{unit}:", "\tDefaults:", f"\t\tFilename: sprites/{unit}.png"]
    for seq_name, start, length, facings, tick, stride in seq_defs:
        lines.append(f"\t{seq_name}:")
        lines.append(f"\t\tStart: {start}")
        if length != 1:
            lines.append(f"\t\tLength: {length}")
        if facings != 1:
            lines.append(f"\t\tFacings: {facings}")
        if stride is not None:
            lines.append(f"\t\tStride: {stride}")
        if tick is not None:
            lines.append(f"\t\tTick: {tick}")
    if icon_cells is not None:
        _, start, length, facings, tick, _ = icon_defs[0]
        lines += ["\ticon:", f"\t\tFilename: sprites/{unit}-icon.png", f"\t\tStart: {start}"]
        if length != 1:
            lines.append(f"\t\tLength: {length}")
        if tick is not None:
            lines.append(f"\t\tTick: {tick}")
        seq_defs.append(("icon", start, length, facings, tick, None))
    with open(os.path.join(out_dir, "sequences", f"{unit}.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    return {"unit": unit, "sheet": f"sprites/{unit}.png", "cell": [cw, ch], "cells": len(sheet_cells),
            "sequences": [{"name": n, "start": s, "length": l, "facings": fa, "tick": t} for n, s, l, fa, t, _ in seq_defs]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", required=True, help="path to a terragov-marine-corps checkout")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "mod", "tgmc"))
    ap.add_argument("--units", nargs="*", default=sorted(UNITS))
    args = ap.parse_args()

    report = []
    for unit in args.units:
        info = build_unit(args.tgmc, unit, UNITS[unit], args.out)
        report.append(info)
        print(f"{unit}: {info['cells']} cells of {info['cell'][0]}x{info['cell'][1]}px -> {info['sheet']}")
    with open(os.path.join(args.out, "sprites.json"), "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
