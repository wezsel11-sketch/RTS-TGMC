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
FEET = "icons/mob/clothing/feet.dmi"
RIFLES = "icons/mob/inhands/guns/rifles_right_1.dmi"
SMGS = "icons/mob/inhands/guns/submachineguns_right_1.dmi"
PISTOLS = "icons/mob/inhands/guns/pistols_right_1.dmi"
CRYO = "icons/obj/machines/cryogenics2.dmi"
VENDING = "icons/obj/machines/vending.dmi"
WARRIOR = "icons/Xeno/castes/warrior.dmi"
GRENADE = "icons/obj/items/grenade.dmi"

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


UNITS = {
    "rifleman": {
        "sequences": {
            "stand": marine("marine_jumpsuit", (RIFLES, "t18_w")),
            "run": "stand",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "runner": {
        "sequences": {
            "stand": [(RUNNER, "Runner Walking")],
            "run": [(RUNNER, "Runner Running")],
            "die": [(RUNNER, "Runner Dead")],
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
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "drone": {
        "sequences": {
            "stand": [(DRONE, "Drone Walking")],
            "run": [(DRONE, "Drone Running")],
            "die": [(DRONE, "Drone Dead")],
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
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    # Marine roles. Same body as the rifleman, with the role's uniform state on top.
    "medic": {
        "sequences": {
            "stand": marine("marine_medic", (PISTOLS, "m44")),
            "run": "stand",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "engineer": {
        "sequences": {
            "stand": marine("marine_engineer", (SMGS, "t19_w")),
            "run": "stand",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    # Marine gunners. Same kit as the other roles with their own uniform state; the weapon art is the rifle's.
    "smartgunner": {
        "sequences": {
            "stand": marine("marine_assault_crewman", (RIFLES, "t18_w")),
            "run": "stand",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "grenadier": {
        "sequences": {
            "stand": marine("pilot_spec", (RIFLES, "t18_w")),
            "run": "stand",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    # Marine structures. Sentry is 4-dir (8 facings). Cryo pod and vendor are 1-dir and animate in place.
    "sentry-turret": {
        "sequences": {"turret": [(SENTRY, "sentry_deployed")]},
    },
    "cryo-pod": {
        "sequences": {"idle": [(CRYO, "cell_off")], "active": [(CRYO, "cell_on")]},
    },
    "vendor": {
        "sequences": {"idle": [(VENDING, "sustenance")]},
    },
    # Xeno structures. Turret is 4-dir, so it gets 8 facings; silo and pod are 1-dir and animate in place.
    "resin-turret": {
        "sequences": {"turret": [(ACID_TURRET, "resin_turret")]},
    },
    "resin-silo": {
        "sequences": {"idle": [(RESIN_SILO, "weed_silo")]},
    },
    "mini-silo": {
        "sequences": {"idle": [(RESIN_POD, "resinpod")]},
    },
    # Projectile images. Weapons refer to these by name (Bullet Image:), not as actors.
    "grenade": {
        "sequences": {"idle": [(GRENADE, "grenade")]},
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


def layer_images(dmi, state, tint=None):
    """Return {side: [frame images]} for S/N/E/W, or {"*": [frame images]} for a 1-dir state."""
    frames = dmi.frames(state)
    dirs = dmi.state(state)["dirs"]
    if dirs == 1:
        return {"*": [tinted(frames[f][0], tint) for f in range(len(frames))]}
    if dirs != 4:
        raise SystemExit(f"{dmi.path}:{state} has {dirs} dirs; only 1 or 4 are handled")
    return {name: [tinted(frames[f][d], tint) for f in range(len(frames))] for d, name in enumerate(tgmc_dmi.DIRS4)}


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


def build_unit(tgmc, unit, spec, out_dir):
    sheet_cells = []      # PIL images, appended in cell order
    cell_size = None  # (width, height) of one cell
    seq_defs = []         # (sequence name, start, length, facings, tick or None, stride or None)
    aliases = []
    for seq_name, layer_specs in spec["sequences"].items():
        if isinstance(layer_specs, str):
            aliases.append((seq_name, layer_specs))
            continue
        dmis = [(tgmc_dmi.Dmi(os.path.join(tgmc, spec[0])), spec[1]) for spec in layer_specs]
        layers = [(dmi, state, layer_images(dmi, state, spec[2] if len(spec) > 2 else None))
                  for (dmi, state), spec in zip(dmis, layer_specs)]
        sides = composite(layers)
        size = (dmis[0][0].icon_w, dmis[0][0].icon_h)
        if cell_size is None:
            cell_size = size
        elif cell_size != size:
            raise SystemExit(f"{unit}: mixed icon sizes {cell_size} and {size}")

        if "*" in sides:
            sources = ["*"]
        else:
            sources = [FACING_SOURCE[name] for name in FACING_NAMES]
        tick, order = frame_timing(dmis[0][0].state(dmis[0][1])["delays"])
        if order is None or len(order) < len(sides[sources[0]]):
            tick, order = None, list(range(len(sides[sources[0]])))
        start = len(sheet_cells)
        for source in sources:
            for f in order:
                sheet_cells.append(sides[source][f])
        seq_defs.append((seq_name, start, len(order), len(sources), tick, None))

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

    cols = 8
    rows = (len(sheet_cells) + cols - 1) // cols
    cw, ch = cell_size
    sheet = Image.new("RGBA", (cols * cw, rows * ch), (0, 0, 0, 0))
    for i, img in enumerate(sheet_cells):
        sheet.paste(img, ((i % cols) * cw, (i // cols) * ch))

    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", f"{cw},{ch}")
    meta.add_text("FrameAmount", str(len(sheet_cells)))
    os.makedirs(os.path.join(out_dir, "sprites"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "sequences"), exist_ok=True)
    png = os.path.join(out_dir, "sprites", f"{unit}.png")
    sheet.save(png, pnginfo=meta)

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
