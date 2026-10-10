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

Output (default build/mod/tgmc):
  sprites/<unit>.png     sheet; FrameSize and FrameAmount are PNG text chunks
  sequences/<unit>.yaml  OpenRA sequence definitions for the unit

Usage: build_sprites.py --tgmc CHECKOUT [--out DIR]
"""
import argparse
import json
import os
import sys

from PIL import Image, PngImagePlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgmc_dmi  # noqa: E402

HUMAN = "icons/mob/human.dmi"
MARINE_UNIFORM = "icons/mob/clothing/uniforms/marine_uniforms.dmi"
RUNNER = "icons/Xeno/castes/runner.dmi"
ACID_TURRET = "icons/Xeno/acid_turret.dmi"
RESIN_SILO = "icons/Xeno/resin_silo.dmi"
RESIN_POD = "icons/Xeno/resin_pod.dmi"
SENTRY = "icons/obj/machines/deployable/sentry/sentry.dmi"
CRYO = "icons/obj/machines/cryogenics2.dmi"
VENDING = "icons/obj/machines/vending.dmi"
HUNTER = "icons/Xeno/castes/hunter.dmi"
SPITTER = "icons/Xeno/castes/spitter.dmi"
WARRIOR = "icons/Xeno/castes/warrior.dmi"
XENO_EFFECTS = "icons/Xeno/Effects.dmi"
GRENADE = "icons/obj/items/grenade.dmi"

# OpenRA facing order (clockwise from north) -> which TGMC side to draw.
FACING_NAMES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
FACING_SOURCE = {"N": "N", "NE": "E", "E": "E", "SE": "E", "S": "S", "SW": "W", "W": "W", "NW": "W"}

# unit -> sequence -> list of (dmi path, state name) layers, bottom first.
# A sequence given as a string reuses another sequence's cells (an alias, no new art).
UNITS = {
    "rifleman": {
        "sequences": {
            "stand": [(HUMAN, "body_m"), (MARINE_UNIFORM, "marine_jumpsuit")],
            "run": [(HUMAN, "body_m"), (MARINE_UNIFORM, "marine_jumpsuit")],
            "attack": "stand",
            "icon": "stand",
        },
    },
    "runner": {
        "sequences": {
            "stand": [(RUNNER, "Runner Walking")],
            "run": [(RUNNER, "Runner Running")],
            "die": [(RUNNER, "Runner Dead")],
            "attack": [(RUNNER, "alien_fire")],
            "icon": "stand",
        },
    },
    # Xeno castes. Each has its own alien_fire (4-dir, 5 frames) for its attack animation.
    "hunter": {
        "sequences": {
            "stand": [(HUNTER, "Hunter Walking")],
            "run": [(HUNTER, "Hunter Running")],
            "die": [(HUNTER, "Hunter Dead")],
            "attack": [(HUNTER, "alien_fire")],
            "icon": "stand",
        },
    },
    "spitter": {
        "sequences": {
            "stand": [(SPITTER, "Spitter Walking")],
            "run": [(SPITTER, "Spitter Running")],
            "die": [(SPITTER, "Spitter Dead")],
            "attack": [(SPITTER, "alien_fire")],
            "icon": "stand",
        },
    },
    "warrior": {
        "sequences": {
            "stand": [(WARRIOR, "Warrior Walking")],
            "run": [(WARRIOR, "Warrior Running")],
            "die": [(WARRIOR, "Warrior Dead")],
            "attack": [(WARRIOR, "alien_fire")],
            "icon": "stand",
        },
    },
    # Marine gunners. Same body as the rifleman, with a different uniform state on top.
    "smartgunner": {
        "sequences": {
            "stand": [(HUMAN, "body_m"), (MARINE_UNIFORM, "marine_assault_crewman")],
            "run": [(HUMAN, "body_m"), (MARINE_UNIFORM, "marine_assault_crewman")],
            "attack": "stand",
            "icon": "stand",
        },
    },
    "grenadier": {
        "sequences": {
            "stand": [(HUMAN, "body_m"), (MARINE_UNIFORM, "pilot_spec")],
            "run": [(HUMAN, "body_m"), (MARINE_UNIFORM, "pilot_spec")],
            "attack": "stand",
            "icon": "stand",
        },
    },
    # Xeno structures. Turret is 4-dir, so it gets 8 facings; silo and pod are 1-dir and animate in place.
    # Marine roles. Same body as the rifleman, with the role's uniform state on top.
    "medic": {
        "sequences": {
            "stand": [(HUMAN, "body_m"), (MARINE_UNIFORM, "marine_medic")],
            "run": [(HUMAN, "body_m"), (MARINE_UNIFORM, "marine_medic")],
            "attack": "stand",
            "icon": "stand",
        },
    },
    "engineer": {
        "sequences": {
            "stand": [(HUMAN, "body_m"), (MARINE_UNIFORM, "marine_engineer")],
            "run": [(HUMAN, "body_m"), (MARINE_UNIFORM, "marine_engineer")],
            "attack": "stand",
            "icon": "stand",
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
    "acidspit": {
        "sequences": {"idle": [(XENO_EFFECTS, "acidblob")]},
    },
    "grenade": {
        "sequences": {"idle": [(GRENADE, "grenade")]},
    },
}


def layer_images(dmi, state):
    """Return {side: [frame images]} for S/N/E/W, or {"*": [frame images]} for a 1-dir state."""
    frames = dmi.frames(state)
    dirs = dmi.state(state)["dirs"]
    if dirs == 1:
        return {"*": [frames[f][0] for f in range(len(frames))]}
    if dirs != 4:
        raise SystemExit(f"{dmi.path}:{state} has {dirs} dirs; only 1 or 4 are handled")
    return {name: [frames[f][d] for f in range(len(frames))] for d, name in enumerate(tgmc_dmi.DIRS4)}


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


def build_unit(tgmc, unit, spec, out_dir):
    sheet_cells = []      # PIL images, appended in cell order
    cell_size = None  # (width, height) of one cell
    seq_defs = []         # (sequence name, start, length, facings)
    aliases = []
    for seq_name, layer_specs in spec["sequences"].items():
        if isinstance(layer_specs, str):
            aliases.append((seq_name, layer_specs))
            continue
        dmis = [(tgmc_dmi.Dmi(os.path.join(tgmc, path)), state) for path, state in layer_specs]
        layers = [(dmi, state, layer_images(dmi, state)) for dmi, state in dmis]
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
        frame_count = len(sides[sources[0]])
        start = len(sheet_cells)
        for source in sources:
            for f in range(frame_count):
                sheet_cells.append(sides[source][f])
        seq_defs.append((seq_name, start, frame_count, len(sources)))

    starts = {name: (start, length, facings) for name, start, length, facings in seq_defs}
    for alias, target in aliases:
        start, length, facings = starts[target]
        seq_defs.append((alias, start, length, facings))

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
    for seq_name, start, length, facings in seq_defs:
        lines.append(f"\t{seq_name}:")
        lines.append(f"\t\tStart: {start}")
        if length != 1:
            lines.append(f"\t\tLength: {length}")
        if facings != 1:
            lines.append(f"\t\tFacings: {facings}")
    with open(os.path.join(out_dir, "sequences", f"{unit}.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    return {"unit": unit, "sheet": f"sprites/{unit}.png", "cell": [cw, ch], "cells": len(sheet_cells),
            "sequences": [{"name": n, "start": s, "length": l, "facings": fa} for n, s, l, fa in seq_defs]}


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
