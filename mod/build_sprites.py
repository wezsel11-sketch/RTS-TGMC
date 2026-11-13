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
square, "centre" (w, h) centres them on a transparent canvas of that size, "fit" (w, h) shrinks them into a box of that size keeping the aspect ratio, "side" keeps one side (S, N, E, W) of a
4-direction state, and "tick" sets the milliseconds per frame. On the first layer of a sequence, "fade" (N) turns the composited still pose
into N frames that fade out, "fall" (N) turns it into N frames that topple onto its side. A unit may also carry "cell": (w, h), which centres every frame of its sheet on a cell that
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

from PIL import Image, ImageChops, ImageDraw, ImageFilter, PngImagePlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgmc_dmi  # noqa: E402
from build_tileset import CAVE_JUNCTIONS  # noqa: E402

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
MORTAR = "icons/obj/machines/deployable/mortar.dmi"
HOWITZER = "icons/obj/machines/deployable/howitzer.dmi"
MARINE_ARMOR = "icons/mob/clothing/suits/marine_armor.dmi"
MARINE_HELMETS = "icons/mob/clothing/headwear/marine_helmets.dmi"
HUMAN_GIB = "icons/mob/human_gib.dmi"
FEET = "icons/mob/clothing/feet.dmi"
RIFLES = "icons/mob/inhands/guns/rifles_right_1.dmi"
MG60 = "icons/mob/inhands/guns/machineguns_right_64.dmi"
MARKSMAN = "icons/mob/inhands/guns/marksman_right_64.dmi"
SADAR = "icons/mob/inhands/guns/special_right_64.dmi"
VALI = "icons/mob/inhands/weapons/vali_right.dmi"
FLAMER = "icons/mob/inhands/guns/special_right_1.dmi"
SMGS = "icons/mob/inhands/guns/submachineguns_right_1.dmi"
SHOTGUNS = "icons/mob/inhands/guns/shotguns_right_1.dmi"
PISTOLS = "icons/mob/inhands/guns/pistols_right_1.dmi"
# The left-hand sheets: a two-handed gun has the same wielded state on the right and the left sheet (see guns()).
TWO_HANDED_LEFT = {
    RIFLES: "icons/mob/inhands/guns/rifles_left_1.dmi",
    MG60: "icons/mob/inhands/guns/machineguns_left_64.dmi",
    MARKSMAN: "icons/mob/inhands/guns/marksman_left_64.dmi",
    SADAR: "icons/mob/inhands/guns/special_left_64.dmi",
    FLAMER: "icons/mob/inhands/guns/special_left_1.dmi",
    SMGS: "icons/mob/inhands/guns/submachineguns_left_1.dmi",
    SHOTGUNS: "icons/mob/inhands/guns/shotguns_left_1.dmi",
}
CRYO = "icons/obj/machines/cryogenics2.dmi"
VENDING = "icons/obj/machines/vending.dmi"
WARRIOR = "icons/Xeno/castes/warrior.dmi"
GRENADE = "icons/obj/items/grenade.dmi"
PROJECTILES = "icons/obj/items/projectiles.dmi"
# The guns as items lying on the ground: the icons of the Upgrades tab.
GUN_ITEMS = "icons/obj/items/guns/rifles.dmi"
GUN_ITEMS_64 = "icons/obj/items/guns/rifles64.dmi"
SMG_ITEMS_64 = "icons/obj/items/guns/submachineguns64.dmi"
SMG_ITEMS = "icons/obj/items/guns/submachineguns.dmi"
SHOTGUN_ITEMS_64 = "icons/obj/items/guns/shotguns64.dmi"
SHOTGUN_ITEMS = "icons/obj/items/guns/shotguns.dmi"
SPECIAL_ITEMS = "icons/obj/items/guns/special.dmi"
SPECIAL_ITEMS_64 = "icons/obj/items/guns/special64.dmi"
MG_ITEMS_64 = "icons/obj/items/guns/machineguns64.dmi"
MARKSMAN_ITEMS_64 = "icons/obj/items/guns/marksman64.dmi"
MARKSMAN_ITEMS = "icons/obj/items/guns/marksman.dmi"
ARMOR_ITEMS = "icons/obj/clothing/suits/marine_armor.dmi"
FX64 = "icons/effects/64x64.dmi"
FX96 = "icons/effects/96x96.dmi"
FX32 = "icons/effects/effects.dmi"
FIRE = "icons/effects/fire.dmi"
BLOOD = "icons/effects/blood.dmi"
DROPPOD = "icons/obj/structures/droppod.dmi"
ARTILLERY = "icons/obj/items/ammo/artillery.dmi"
CHEMSMOKE = "icons/effects/chemsmoke.dmi"
CASINGS = "icons/obj/items/casings.dmi"
HEAVY_IMPACT = "icons/effects/heavyimpact.dmi"
XENO_FX = "icons/Xeno/Effects.dmi"
QUEEN = "icons/Xeno/castes/queen.dmi"
LARVA = "icons/Xeno/castes/larva.dmi"
WEEDS = "icons/Xeno/weeds.dmi"
XENO_2X2 = "icons/Xeno/2x2building.dmi"
SPITTER = "icons/Xeno/castes/spitter.dmi"
PRAETORIAN = "icons/Xeno/castes/praetorian.dmi"
CRUSHER = "icons/Xeno/castes/crusher.dmi"
RAVAGER = "icons/Xeno/castes/ravager.dmi"
DEFILER = "icons/Xeno/castes/defiler.dmi"
BOILER = "icons/Xeno/castes/boiler.dmi"
CARRIER = "icons/Xeno/castes/carrier.dmi"
WARLOCK = "icons/Xeno/castes/warlock.dmi"
SHRIKE = "icons/Xeno/castes/shrike.dmi"
WIDOW = "icons/Xeno/castes/widow.dmi"
WRAITH = "icons/Xeno/castes/wraith.dmi"
BULL = "icons/Xeno/castes/bull.dmi"
BEHEMOTH = "icons/Xeno/castes/behemoth.dmi"
RESIN_WALL = "icons/obj/smooth_objects/resin-wall.dmi"
RESIN_DOOR = "icons/obj/smooth_objects/resin-door.dmi"
# How far below the units each flat ground layer sorts (OpenRA sorts by Y + ZOffset, 1024 a cell). It must be more than a unit's
# sprite reaches below its feet cell, or the carpet of the next row south is drawn over its legs; at -1023 it was not. Lowest first,
# so blood lies on weeds and a shadow on blood. Footprints are drawn in code (GroundFx.cs Decal) at -14500.
GROUND_Z = {"weeds": -16384, "sticky": -16000, "blood": -15000, "gibs": -14000, "shadow": -13000}
APC = "icons/obj/armored/3x3/apc.dmi"
APC_CUPOLA = {"N": "cupola_1", "S": "cupola_2", "E": "cupola_4", "W": "cupola_8"}
CADE = "icons/obj/structures/barricades/metal.dmi"
MECH_MEDIUM = "icons/mecha/mech_medium.dmi"
MECH_WEAPONS = "icons/mecha/mech_core_weapons.dmi"

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
# The cloth layers were tinted here once, one colour per faction. Units are now tinted per player when drawn (WithPlayerTint in
# tgmc/code/PlayerTint.cs), so the sheets stay neutral. The names still mark which layers are cloth.
# Layers marked CLOTH take the owner's colour in the game: they are drawn untinted here and again, in grey, on the unit's
# "<unit>-cloth" sheet, which WithPlayerTint (tgmc/code/PlayerTint.cs) draws over the unit in the player colour.
CLOTH = "cloth"
MARINE_TEAM = CLOTH
XENO_TEAM = None
SOM_TEAM = CLOTH
SOM_ARMOR = "icons/mob/modular/som_armor.dmi"
SOM_HELMETS = "icons/mob/modular/som_helmets.dmi"
GEAR = [(MARINE_ARMOR, "xarmor", MARINE_TEAM), (FEET, "marine"), (MARINE_HELMETS, "helmet", MARINE_TEAM)]


def centred(layer, size=(64, 32)):
    """The layer with the "centre" option, so it lines up under a gun drawn on a 64px canvas."""
    parts = list(layer) + [None] * (3 - len(layer))
    opts = dict(parts[3]) if len(parts) > 3 else {}
    opts["centre"] = size
    return tuple(parts[:3]) + (opts,)


def guns(weapon):
    """The layers a gun adds to a marine. A two-handed gun is TGMC's wielded state, which both its right-hand and its left-hand sheet
    draw; drawing both made the marine look like he carried two guns, so each facing uses the one that shows the gun better. TGMC's gun
    sheets hold no hands, only the gun, so the marine's arms stay at his sides."""
    left = TWO_HANDED_LEFT.get(weapon[0])
    if not left:
        return [weapon]

    # One gun, not one per hand: for each facing, the sheet (right hand or left hand) that shows the gun better.
    parts = list(weapon) + [None] * (3 - len(weapon))
    opts = dict(parts[3]) if len(parts) > 3 and parts[3] else {}
    opts["or_sheet"] = left
    return [(weapon[0], weapon[1], parts[2], opts)]


def with_gun(body, weapon):
    """The marine's body layers plus his gun. A 64px in-hand gun (the sniper rifle, SADAR, machine guns) is drawn full size, as
    TGMC does, on a 64x32 canvas, so the 32px body is centred on that canvas; shrinking the gun to the marine's size, as before,
    made it a toy."""
    if len(weapon) > 3 and weapon[3].get("big"):
        body = [centred(layer) for layer in body]
    return body + guns(weapon)


def marine(uniform, weapon):
    """Body, role uniform, armour, boots and helmet, then the weapon held in the hands."""
    return with_gun([(HUMAN, "body_m"), (MARINE_UNIFORM, uniform, MARINE_TEAM)] + GEAR, weapon)


JAEGER = "icons/mob/modular/mark_two/{}.dmi"


def jaeger(pattern, weapon):
    """A Jaeger Mk.II marine: body, uniform, the pattern's chest plate and helmet (a greyscale sheet, tinted with the team colour), boots,
    then the weapon. Patterns: scout, skirmisher, trooper (light); infantry, eva, ranger, helljumper (medium); gugnir, assault, eod (heavy)."""
    dmi = JAEGER.format(pattern)
    return with_gun([(HUMAN, "body_m"), (MARINE_UNIFORM, "marine_jumpsuit", MARINE_TEAM), (dmi, "chest", MARINE_TEAM),
                     (FEET, "marine"), (dmi, "helm", MARINE_TEAM)], weapon)


def som(armor, helmet, weapon):
    """A Son of Mars: body, red uniform, TGMC's SOM armour and helmet (black), boots, then the weapon."""
    return with_gun([(HUMAN, "body_m"), (MARINE_UNIFORM, "marine_jumpsuit", SOM_TEAM), (SOM_ARMOR, armor),
                     (FEET, "marine"), (SOM_HELMETS, helmet)], weapon)


# Presets for the mech: the accent colours painted on TGMC's medium mech, and the two weapons on its arms.
MECH_PRESETS = {
    "assault": {"trim": (205, 205, 215), "right": "assaultrifle_right", "left": "rocketlauncher_left"},
    "flame": {"trim": (255, 215, 90), "right": "shotgun_right", "left": "flamer_left"},
    "support": {"trim": (205, 235, 175), "right": "smg_right", "left": "rpg_left"},
    "tow": {"trim": (90, 95, 115), "right": "assaultrifle_right", "left": "tow_left"},
    # The Sons of Mars' walker: the same four builds in SOM red and black.
    "som_assault": {"trim": (40, 40, 45), "right": "assaultrifle_right", "left": "rocketlauncher_left"},
    "som_flame": {"trim": (255, 150, 60), "right": "shotgun_right", "left": "flamer_left"},
    "som_support": {"trim": (60, 60, 65), "right": "smg_right", "left": "rpg_left"},
    "som_tow": {"trim": (30, 30, 35), "right": "assaultrifle_right", "left": "tow_left"},
}


def mech(preset):
    """TGMC's medium mech in one of the MECH_PRESETS. Each part is a dark frame (the "nocolor" states, which are the mech's
    skeleton) and two thin paint masks, which get the preset's accent colours. The weapons come from another sheet of the same
    96x96 size and are laid on top."""
    spec = MECH_PRESETS[preset]
    trim = spec["trim"]
    opts = {"pad": (96, 96), "scale": 1.0}
    stack = []
    for part, frame in (("legs", "legsnocolor"), ("core", "corenocolor"), ("head", "headnocolor"), ("leftarm", "leftarmnocolor"),
                        ("rightarm", "rightarmnocolor")):
        # The main paint is the owner's colour (CLOTH); the preset's own paint colour is no longer used on the map sprite.
        stack += [(frame, None), (f"{part}primary", CLOTH), (f"{part}secondary", trim)]
    stack += [("visor", None)]
    layers = [(MECH_MEDIUM, state, tint, dict(opts)) for state, tint in stack]
    layers += [(MECH_WEAPONS, spec["right"], None, dict(opts)), (MECH_WEAPONS, spec["left"], None, dict(opts))]
    return layers


def fallen(layers):
    """The same stack with its first layer (the body) topping over, for a marine's death: TGMC has no lying-down human."""
    first = layers[0]
    return [(first[0], first[1], None, {**(first[3] if len(first) > 3 else {}), "fall": 6, "tick": 90})] + layers[1:]


# TGMC's human gib is 64px and the marine is 32px, so the marine sheets hold 64px cells.
MARINE_CELL = (64, 64)
MARINE_GIB = [(HUMAN_GIB, "default", None, {"tick": 70})]

UNITS = {
    "rifleman": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_jumpsuit", (RIFLES, "t12_w")),
            "stand-carbine": marine("marine_jumpsuit", (RIFLES, "t18_w")),
            "stand-m412": marine("marine_jumpsuit", (RIFLES, "m412_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    # The Upgrades tab (tgmc/rules/upgrades.yaml): the gun each upgrade issues.
    # (build_unit wants a main sequence beside the icon, so each also has an idle frame that nothing draws.)
    "upgrade-rifle-t12": {"sequences": {"idle": [(GUN_ITEMS, "t12")], "icon": [(GUN_ITEMS, "t12", None, {"fit": (44, 44)})]}},
    "upgrade-carapace-1": {"sequences": {"idle": [(CRUSHER, "Crusher Walking")], "icon": [(CRUSHER, "Crusher Walking", None, {"side": "S", "frames": (0, 1), "fit": (44, 44)})]}},
    "upgrade-carapace-2": {"sequences": {"idle": [(RAVAGER, "Ravager Walking")], "icon": [(RAVAGER, "Ravager Walking", None, {"side": "S", "frames": (0, 1), "fit": (44, 44)})]}},
    "upgrade-claws": {"sequences": {"idle": [(WARRIOR, "Warrior Walking")], "icon": [(WARRIOR, "Warrior Walking", None, {"side": "S", "frames": (0, 1), "fit": (44, 44)})]}},
    "upgrade-hive-speed": {"sequences": {"idle": [(RUNNER, "Runner Running")], "icon": [(RUNNER, "Runner Running", None, {"side": "S", "frames": (0, 1), "fit": (44, 44)})]}},
    "upgrade-rifle-m412": {"sequences": {"idle": [(GUN_ITEMS_64, "m412")], "icon": [(GUN_ITEMS_64, "m412", None, {"fit": (44, 44)})]}},
    "upgrade-smg-m25": {"sequences": {"idle": [(SMG_ITEMS_64, "m25")], "icon": [(SMG_ITEMS_64, "m25", None, {"fit": (44, 44)})]}},
    "upgrade-shotgun-sh410": {"sequences": {"idle": [(SHOTGUN_ITEMS_64, "sh410")], "icon": [(SHOTGUN_ITEMS_64, "sh410", None, {"fit": (44, 44)})]}},
    "upgrade-mg-minigun": {"sequences": {"idle": [(SPECIAL_ITEMS_64, "minigun")], "icon": [(SPECIAL_ITEMS_64, "minigun", None, {"fit": (44, 44)})]}},
    "upgrade-rocket-heavy": {"sequences": {"idle": [(SPECIAL_ITEMS_64, "iccrpg")], "icon": [(SPECIAL_ITEMS_64, "iccrpg", None, {"fit": (44, 44)})]}},
    "upgrade-smg-t90": {"sequences": {"idle": [(SMG_ITEMS, "t90")], "icon": [(SMG_ITEMS, "t90", None, {"fit": (44, 44)})]}},
    "upgrade-sniper-svd": {"sequences": {"idle": [(MARKSMAN_ITEMS_64, "svd")], "icon": [(MARKSMAN_ITEMS_64, "svd", None, {"fit": (44, 44)})]}},
    "upgrade-sniper-tx8": {"sequences": {"idle": [(MARKSMAN_ITEMS_64, "tx8")], "icon": [(MARKSMAN_ITEMS_64, "tx8", None, {"fit": (44, 44)})]}},
    "upgrade-sniper-m42c": {"sequences": {"idle": [(MARKSMAN_ITEMS, "m42c")], "icon": [(MARKSMAN_ITEMS, "m42c", None, {"fit": (44, 44)})]}},
    "upgrade-shotgun-tx15": {"sequences": {"idle": [(SHOTGUN_ITEMS, "tx15")], "icon": [(SHOTGUN_ITEMS, "tx15", None, {"fit": (44, 44)})]}},
    "upgrade-flamer-xnapalm": {"sequences": {"idle": [(SPECIAL_ITEMS, "m240")], "icon": [(SPECIAL_ITEMS, "m240", None, {"fit": (44, 44)})]}},
    "upgrade-armor-1": {"sequences": {"idle": [(ARMOR_ITEMS, "tanker")], "icon": [(ARMOR_ITEMS, "tanker", None, {"fit": (44, 44)})]}},
    "upgrade-armor-2": {"sequences": {"idle": [(ARMOR_ITEMS, "xarmor")], "icon": [(ARMOR_ITEMS, "xarmor", None, {"fit": (44, 44)})]}},
    "upgrade-armor-3": {"sequences": {"idle": [(ARMOR_ITEMS, "marine_riot")], "icon": [(ARMOR_ITEMS, "marine_riot", None, {"fit": (44, 44)})]}},
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
    "spitter": {
        "sequences": {
            "walk": [(SPITTER, "Spitter Walking")],
            "run": [(SPITTER, "Spitter Running")],
            "stand": "walk#1",
            "die": [(SPITTER, "Spitter Dead")],
            "die-gib": [(SPITTER, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "praetorian": {
        "sequences": {
            "walk": [(PRAETORIAN, "Praetorian Walking")],
            "run": [(PRAETORIAN, "Praetorian Running")],
            "stand": "walk#1",
            "die": [(PRAETORIAN, "Praetorian Dead")],
            "die-gib": [(PRAETORIAN, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "crusher": {
        "sequences": {
            "walk": [(CRUSHER, "Crusher Walking")],
            "run": [(CRUSHER, "Crusher Running")],
            "stand": "walk#1",
            "die": [(CRUSHER, "Crusher Dead")],
            "die-gib": [(CRUSHER, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "ravager": {
        "sequences": {
            "walk": [(RAVAGER, "Ravager Walking")],
            "run": [(RAVAGER, "Ravager Running")],
            "stand": "walk#1",
            "die": [(RAVAGER, "Ravager Dead")],
            "die-gib": [(RAVAGER, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "defiler": {
        "sequences": {
            "walk": [(DEFILER, "Defiler Walking")],
            "run": [(DEFILER, "Defiler Running")],
            "stand": "walk#1",
            "die": [(DEFILER, "Defiler Dead")],
            "die-gib": [(DEFILER, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "boiler": {
        "sequences": {
            "walk": [(BOILER, "Boiler Walking")],
            "run": [(BOILER, "Boiler Running")],
            "stand": "walk#1",
            "die": [(BOILER, "Boiler Dead")],
            "die-gib": [(BOILER, "gibbed-a-boiler", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "carrier": {
        "sequences": {
            "walk": [(CARRIER, "Carrier Walking")],
            "run": [(CARRIER, "Carrier Running")],
            "stand": "walk#1",
            "die": [(CARRIER, "Carrier Dead")],
            "die-gib": [(CARRIER, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "warlock": {
        "sequences": {
            "walk": [(WARLOCK, "Warlock Walking")],
            "run": [(WARLOCK, "Warlock Running")],
            "stand": "walk#1",
            "die": [(WARLOCK, "Warlock Dead")],
            "die-gib": [(WARLOCK, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "shrike": {
        "sequences": {
            "walk": [(SHRIKE, "Shrike Walking")],
            "run": [(SHRIKE, "Shrike Running")],
            "stand": "walk#1",
            "die": [(SHRIKE, "Shrike Dead")],
            "die-gib": [(SHRIKE, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "widow": {
        "sequences": {
            "walk": [(WIDOW, "Widow Walking")],
            "run": [(WIDOW, "Widow Running")],
            "stand": "walk#1",
            "die": [(WIDOW, "Widow Dead")],
            "die-gib": [(WIDOW, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "wraith": {
        "sequences": {
            "walk": [(WRAITH, "Wraith Walking")],
            "run": [(WRAITH, "Wraith Running")],
            "stand": "walk#1",
            "die": [(WRAITH, "Wraith Dead")],
            "die-gib": [(WRAITH, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    # The castes added from TGMC's caste sheets (units.yaml, "castes from TGMC"): walk, run, die and, where TGMC has one, a gib.
    "baneling": {
        "sequences": {
            "walk": [("icons/Xeno/castes/baneling.dmi", "Baneling Walking")],
            "run": [("icons/Xeno/castes/baneling.dmi", "Baneling Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/baneling.dmi", "Baneling Dead")],
            "die-gib": "die",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "beetle": {
        "sequences": {
            "walk": [("icons/Xeno/castes/beetle.dmi", "Beetle Walking")],
            "run": [("icons/Xeno/castes/beetle.dmi", "Beetle Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/beetle.dmi", "Beetle Dead")],
            "die-gib": [("icons/Xeno/castes/beetle.dmi", "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "defender": {
        "sequences": {
            "walk": [("icons/Xeno/castes/defender.dmi", "Defender Walking")],
            "run": [("icons/Xeno/castes/defender.dmi", "Defender Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/defender.dmi", "Defender Dead")],
            "die-gib": [("icons/Xeno/castes/defender.dmi", "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "dragon": {
        "sequences": {
            "walk": [("icons/Xeno/castes/dragon.dmi", "Dragon Walking")],
            "run": [("icons/Xeno/castes/dragon.dmi", "Dragon Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/dragon.dmi", "Dragon Dead")],
            "die-gib": [("icons/Xeno/castes/dragon.dmi", "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "gorger": {
        "sequences": {
            "walk": [("icons/Xeno/castes/gorger.dmi", "Gorger Walking")],
            "run": [("icons/Xeno/castes/gorger.dmi", "Gorger Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/gorger.dmi", "Gorger Dead")],
            "die-gib": [("icons/Xeno/castes/gorger.dmi", "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "hivelord": {
        "sequences": {
            "walk": [("icons/Xeno/castes/hivelord.dmi", "Hivelord Walking")],
            "run": [("icons/Xeno/castes/hivelord.dmi", "Hivelord Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/hivelord.dmi", "Hivelord Dead")],
            "die-gib": [("icons/Xeno/castes/hivelord.dmi", "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "mantis": {
        "sequences": {
            "walk": [("icons/Xeno/castes/mantis.dmi", "Mantis Walking")],
            "run": [("icons/Xeno/castes/mantis.dmi", "Mantis Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/mantis.dmi", "Mantis Dead")],
            "die-gib": [("icons/Xeno/castes/mantis.dmi", "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "nymph": {
        "sequences": {
            "walk": [("icons/Xeno/castes/nymph.dmi", "Nymph Walking")],
            "run": [("icons/Xeno/castes/nymph.dmi", "Nymph Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/nymph.dmi", "Nymph Dead")],
            "die-gib": [("icons/Xeno/castes/nymph.dmi", "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "puppeteer": {
        "sequences": {
            "walk": [("icons/Xeno/castes/puppeteer.dmi", "Puppeteer Walking")],
            "run": [("icons/Xeno/castes/puppeteer.dmi", "Puppeteer Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/puppeteer.dmi", "Puppeteer Dead")],
            "die-gib": [("icons/Xeno/castes/puppeteer.dmi", "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "pyrogen": {
        "sequences": {
            "walk": [("icons/Xeno/castes/pyrogen.dmi", "Pyrogen Walking")],
            "run": [("icons/Xeno/castes/pyrogen.dmi", "Pyrogen Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/pyrogen.dmi", "Pyrogen Dead")],
            "die-gib": "die",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "scorpion": {
        "sequences": {
            "walk": [("icons/Xeno/castes/scorpion.dmi", "Scorpion Walking")],
            "run": [("icons/Xeno/castes/scorpion.dmi", "Scorpion Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/scorpion.dmi", "Scorpion Dead")],
            "die-gib": [("icons/Xeno/castes/scorpion.dmi", "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "king": {
        "sequences": {
            "walk": [("icons/Xeno/castes/king/king.dmi", "King Walking")],
            "run": [("icons/Xeno/castes/king/king.dmi", "King Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/king/king.dmi", "King Dead")],
            "die-gib": "die",  # too heavy to gib
            "attack": [("icons/Xeno/castes/king/king.dmi", "King Screeching")],
            "icon": "stand:S",
        },
    },
    # The puppeteer's minion: a small husk that runs at the enemy and falls apart after a while.
    "puppet": {
        "sequences": {
            "walk": [("icons/Xeno/castes/puppet.dmi", "Puppet Running")],
            "run": [("icons/Xeno/castes/puppet.dmi", "Puppet Running")],
            "stand": "walk#1",
            "die": [("icons/Xeno/castes/puppet.dmi", "Puppet Dead")],
            "die-gib": "die",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    # The widow's spiderling (Birth Spiderling), from the xeno effects sheet.
    "spiderling": {
        "sequences": {
            "walk": [(XENO_FX, "spiderling Running")],
            "run": [(XENO_FX, "spiderling Running")],
            "stand": [(XENO_FX, "spiderling Walking")],
            "die": [(XENO_FX, "spiderling Dead")],
            "die-gib": "die",
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    # Vehicles from TGMC's armoured sheets (four facings each): the marine tank and APC, and the SOM tank. Hull and turret are
    # separate images (their sheets have different frame sizes); the turret turns on its own (WithSpriteTurret).
    "tank": {
        "sequences": {
            "idle": [("icons/obj/armored/3x3/tank.dmi", "tank")],
            "wreck": [("icons/obj/armored/3x3/tank.dmi", "tank_wreck")],
            "icon": [("icons/obj/armored/3x3/tank.dmi", "tank", None, {"side": "S", "fit": (46, 46)})],
        },
    },
    # A vehicle turret is laid out as TGMC draws it (build_vehicle_turret): the turret body and the cannon on one canvas centred on the hull.
    "tank-turret": {
        "vehicle_turret": {"hull": ("icons/obj/armored/3x3/tank.dmi", "tank"), "body": "turret", "cannon": "ltb_cannon",
                           "gun": "icons/obj/armored/3x3/tank_gun.dmi"},
        "sequences": {"turret": [("icons/obj/armored/3x3/tank_gun.dmi", "turret"), ("icons/obj/armored/3x3/tank_gun.dmi", "ltb_cannon")]},
    },
    # TGMC's troop APC, the Athena (3x3, the tank's size), with its cupola gun mount. TGMC draws the cupola in a different place for
    # each hull direction (cupola_1 north, _2 south, _4 east, _8 west), so it is part of the hull here, pointing where the hull points.
    "apc": {
        "sequences": {
            "idle": [(APC, "apc"), (APC, "cupola_1", None, {"by_side": APC_CUPOLA})],
            # TGMC has no APC wreck: the hull, burnt dark.
            "wreck": [(APC, "apc", (90, 85, 80)), (APC, "cupola_1", (90, 85, 80), {"by_side": APC_CUPOLA})],
            "icon": [(APC, "apc", None, {"side": "S", "fit": (46, 46)})],
        },
    },
    "som-tank": {
        "sequences": {
            "idle": [("icons/obj/armored/3x4/som_tank.dmi", "tank")],
            "wreck": [("icons/obj/armored/3x4/som_tank.dmi", "tank_wreck")],
            "icon": [("icons/obj/armored/3x4/som_tank.dmi", "tank", None, {"side": "S", "fit": (46, 46)})],
        },
    },
    # The SOM hull carries its own turret ring, and TGMC's coilgun pictures each fit only the hull view they were drawn for (a gun
    # aimed north over a hull facing east floats off it). So the SOM tank turns to fire: its body sequence is hull and coilgun together.
    "som-tank-turret": {
        "vehicle_turret": {"hull": ("icons/obj/armored/3x4/som_tank.dmi", "tank"), "body": None, "cannon": "coilgun",
                           "gun": "icons/obj/armored/3x4/som_tank_gun.dmi", "with_hull": True, "sequence": "armed"},
        "sequences": {"turret": [("icons/obj/armored/3x4/som_tank_gun.dmi", "coilgun")]},
    },
    "bull": {
        "sequences": {
            "walk": [(BULL, "Bull Walking")],
            "run": [(BULL, "Bull Running")],
            "stand": "walk#1",
            "die": [(BULL, "Bull Dead")],
            "die-gib": [(BULL, "gibbed-a", None, {"tick": 70})],
            "attack": "stand",
            "icon": "stand:S",
        },
    },
    "behemoth": {
        "sequences": {
            "walk": [(BEHEMOTH, "Behemoth Walking")],
            "run": [(BEHEMOTH, "Behemoth Running")],
            "stand": "walk#1",
            "die": [(BEHEMOTH, "Behemoth Dead")],
            "die-gib": "die",  # too heavy to gib
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
    # Squad leader: a Jaeger infantry pattern with the rifle, the squad's commander (the TGMC squad leader kit).
    "squad_leader": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": jaeger("infantry", (RIFLES, "t12_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    # Field commander: the heavy Jaeger pattern and a sidearm (the TGMC field commander kit).
    "field_commander": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": jaeger("eva", (SMGS, "m25_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    # Sons of Mars (TGMC's SOM armour and helmets; see som()).
    "som_trooper": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_medium_black", "som_helmet_black", (RIFLES, "v31_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_corpsman": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_light_black", "som_helmet_light_black", (SMGS, "m25_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_engineer": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_medium_black", "som_helmet_engineer_black", (SHOTGUNS, "m37_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_veteran": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_heavy_black", "som_helmet_lorica_black", (RIFLES, "v31_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_squad_leader": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_leader_black", "som_helmet_leader_black", (RIFLES, "v31_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_field_commander": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_officer_black", "som_helmet_officer_black", (SMGS, "m25_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    # The rest of the SOM roster (see the SOM plan): the higher tiers.
    "som_smartgunner": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_heavy_black", "som_helmet_black", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_flamer": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_medium_black", "som_helmet_black", (FLAMER, "m240_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_grenadier": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_medium_black", "som_helmet_light_black", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_machinegunner": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_heavy_black", "som_helmet_black", (MG60, "t60_w", None, {"big": True})),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_blademan": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_light_black", "som_helmet_light_black", (VALI, "vali_sword")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_scout": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_light_black", "som_helmet_bio_black", (MARKSMAN, "svd_w", None, {"big": True})),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_mortarman": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_medium_black", "som_helmet_black", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_heavygunner": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_heavy_black", "som_helmet_lorica_black", (MG60, "v41_w", None, {"big": True})),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_rocketeer": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_medium_black", "som_helmet_black", (SADAR, "sadar_100_w", None, {"big": True})),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_demolitionist": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_heavy_black", "som_helmet_engineer_black", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_assault": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_heavy_black", "som_helmet_lorica_black", (RIFLES, "v31_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "som_bomber": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": som("som_light_black", "som_helmet_light_black", (SHOTGUNS, "m37_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 50})],
            "icon": "stand:S",
        },
    },
    "medic": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_medic", (SMGS, "m25_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "icon": "stand:S",
        },
    },
    # The suicide vest: an engineer's build in a tactical vest, with no gun (the detonate ability is the attack).
    "bomber": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_engineer", (SHOTGUNS, "m37_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "icon": "stand:S",
        },
    },
    "engineer": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_engineer", (SHOTGUNS, "m37_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "icon": "stand:S",
        },
    },
    # Marine gunners. Same kit as the other roles with their own uniform state; the weapon art is the rifle's.
    # The synthetic: a white research jumpsuit, no armour and no gun (it carries a baton the game does not draw).
    "synth": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": [(HUMAN, "body_m"), (MARINE_UNIFORM, "research_jumpsuit"), (FEET, "marine")],
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "icon": "stand:S",
        },
    },
    "skirmisher": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_jumpsuit", (SHOTGUNS, "m37_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_flash", None, {"rotate": 90, "facings": 8, "tick": 40})],
            "icon": "stand:S",
        },
    },
    "smartgunner": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_assault_crewman", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_bullet", None, {"rotate": 90, "facings": 8, "tick": 35})],
            "icon": "stand:S",
        },
    },
    "sniper": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_jumpsuit", (MARKSMAN, "svd_w", None, {"big": True})),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_flashold", None, {"rotate": 90, "facings": 8, "tick": 90})],
            "icon": "stand:S",
        },
    },
    "rocketeer": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_jumpsuit", (SADAR, "sadar_100_w", None, {"big": True})),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            # The SADAR's back-blast: a puff of smoke behind the launcher
            "flash": [(PROJECTILES, "recoilless_rifle_smoke", None, {"tick": 60})],
            "icon": "stand:S",
        },
    },
    "blademan": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_jumpsuit", (VALI, "vali_sword")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "icon": "stand:S",
        },
    },
    "mortarman": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_jumpsuit", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "smoke_shell", None, {"tick": 70})],
            "icon": "stand:S",
        },
    },
    "flamer": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_jumpsuit", (FLAMER, "m240_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "spray_flamer", None, {"rotate": 90, "facings": 8, "tick": 40})],
            "icon": "stand:S",
        },
    },
    "machinegunner": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("marine_jumpsuit", (MG60, "t60_w", None, {"big": True})),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_flash", None, {"rotate": 90, "facings": 8, "tick": 40})],
            "icon": "stand:S",
        },
    },
    "grenadier": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": marine("pilot_spec", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            # The grenade launcher's thump: a puff of dust at the muzzle, not a flash
            "flash": [(HEAVY_IMPACT, "heavyimpact", None, {"frames": (0, 9), "size": 32, "tick": 60})],
            "icon": "stand:S",
        },
    },
    "heavygunner": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": jaeger("gugnir", (MG60, "v41_w", None, {"big": True})),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(PROJECTILES, "muzzle_flash", None, {"rotate": 90, "facings": 8, "tick": 30})],
            "icon": "stand:S",
        },
    },
    "demolitionist": {
        "cell": MARINE_CELL,
        "sequences": {
            "stand": jaeger("eod", (RIFLES, "t18_w")),
            "die-gib": MARINE_GIB,
            "run": "stand",
            "attack": "stand",
            "die": [(HUMAN, "husk")],
            "flash": [(HEAVY_IMPACT, "heavyimpact", None, {"frames": (0, 9), "size": 32, "tick": 60})],
            "icon": "stand:S",
        },
    },
    # Marine support buildings and the mech. The mech is TGMC's Durand, a complete 4-direction sprite.
    "mech": {
        "cell": (96, 96),
        "sequences": {
            "stand": mech("assault"),
            "stand-flame": mech("flame"),
            "stand-support": mech("support"),
            "stand-tow": mech("tow"),
            "run": "stand",
            "attack": "stand",
            "die": [(layer[0], layer[1], layer[2], dict(layer[3], fade=10, tick=70)) for layer in mech("assault")],
            "die-gib": "die",
            "flash": [(PROJECTILES, "muzzle_flash", None, {"rotate": 90, "facings": 8, "tick": 30})],
            "icon": "stand:S",
        },
    },
    "som_mech": {
        "cell": (96, 96),
        "sequences": {
            "stand": mech("som_assault"),
            "stand-flame": mech("som_flame"),
            "stand-support": mech("som_support"),
            "stand-tow": mech("som_tow"),
            "run": "stand",
            "attack": "stand",
            "die": [(layer[0], layer[1], layer[2], dict(layer[3], fade=10, tick=70)) for layer in mech("som_assault")],
            "die-gib": "die",
            "flash": [(PROJECTILES, "muzzle_flash", None, {"rotate": 90, "facings": 8, "tick": 30})],
            "icon": "stand:S",
        },
    },
    "medbay": {
        "sequences": {
            "idle": [(VENDING, "marinemed")],
            "icon": [(VENDING, "marinemed", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "ammo-station": {
        "sequences": {
            "idle": [(VENDING, "nanoammo", None, {"side": "S"})],
            "icon": [(VENDING, "nanoammo", None, {"side": "S", "fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "workshop": {
        "sequences": {
            "idle": [(VENDING, "engi")],
            "icon": [(VENDING, "engi", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "recovery-pylon": {
        "sequences": {
            "idle": [(XENO_2X2, "recovery_pylon")],
            "icon": [(XENO_2X2, "recovery_pylon", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "gargoyle": {
        "sequences": {
            "idle": [(XENO_2X2, "gargoyle")],
            "icon": [(XENO_2X2, "gargoyle", None, {"fit": (44, 44), "frames": (0, 1)})],
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
    # Emplacements: a mortar (32px) and a howitzer (64px), each drawn from TGMC's deployed art with its own firing frames, in 8 facings: they turn to face the target.
    "mortar-emplacement": {
        "sequences": {
            "turret": [(MORTAR, "mortar_deployed")],
            "fire": [(MORTAR, "mortar_deployed_fire", None, {"tick": 60})],
            "icon": [(MORTAR, "mortar_deployed", None, {"side": "S", "fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "artillery-emplacement": {
        "sequences": {
            "turret": [(HOWITZER, "howitzer_deployed")],
            "fire": [(HOWITZER, "howitzer_deployed_fire", None, {"tick": 50})],
            "icon": [(HOWITZER, "howitzer_deployed", None, {"side": "S", "fit": (44, 44), "frames": (0, 1)})],
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
    "cade": {
        "sequences": {
            "idle": [(CADE, "metal_0", None, {"side": "S"})],
            "idle-north": [(CADE, "metal_0", None, {"side": "N"})],
            "idle-south": [(CADE, "metal_0", None, {"side": "S"})],
            "idle-east": [(CADE, "metal_0", None, {"side": "E"})],
            "idle-west": [(CADE, "metal_0", None, {"side": "W"})],
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
    "weeds": {
        "zoffset": GROUND_Z["weeds"],  # the carpet lies under everything that walks on it
        "sequences": {
            "idle": [(WEEDS, "weed15")],
            # TGMC's edge pieces, picked by WeedEdges (tgmc/code/Weeds.cs): c<n> joins the neighbours named by the bits of n
            # (BYOND's own numbering: 1 north, 2 south, 4 east, 8 west) and is ragged on the other sides.
            "c0": [(WEEDS, "base")],
            **{f"c{n}": [(WEEDS, f"weed_dir{n}")] for n in range(1, 15)},
            "c15": "idle",
            "icon": [(WEEDS, "weednode3", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    # A hugger egg: shut and ready, opening, and open and empty while the next hugger grows.
    "egg": {
        "sequences": {
            "idle": [(XENO_FX, "egg_hugger2")],
            "open": [(XENO_FX, "egg opening", None, {"tick": 50})],
            "empty": [(XENO_FX, "egg_hugger3")],
            "icon": [(XENO_FX, "egg_hugger2", None, {"fit": (44, 44)})],
        },
    },
    # The carrier's trap: a hole with a hugger in it, empty once sprung.
    "hugger-trap": {
        "sequences": {
            "idle": [(XENO_FX, "traphugger")],
            "open": [(XENO_FX, "traphugger")],
            "empty": [(XENO_FX, "trap")],
            "icon": [(XENO_FX, "traphugger", None, {"fit": (44, 44)})],
        },
    },
    "resin-wall": {
        # One piece for each way a wall cell joins its neighbours, w<TGMC's junction number> (WeedEdges in Weeds.cs picks it).
        "sequences": {
            "idle": [(RESIN_WALL, "resin-wall-0")],
            **{f"w{j}": [(RESIN_WALL, f"resin-wall-{j}")] for j in CAVE_JUNCTIONS},
            "icon": [(RESIN_WALL, "resin-wall-255", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    # TGMC's resin door, the piece with no neighbours (seam north to south) and the one in an east-west wall ("h" sequences).
    "resin-door": {
        "sequences": {
            "resin-closed": [(RESIN_DOOR, "resin-door-0")],
            "resin-opening": [(RESIN_DOOR, "resin-door-0-opening", None, {"tick": 60})],
            "resin-closing": [(RESIN_DOOR, "resin-door-0-closing", None, {"tick": 60})],
            "resin-open": [(RESIN_DOOR, "resin-door-0-open", None, {"side": "S"})],
            "hresin-closed": [(RESIN_DOOR, "resin-door-12")],
            "hresin-opening": [(RESIN_DOOR, "resin-door-12-opening", None, {"tick": 60})],
            "hresin-closing": [(RESIN_DOOR, "resin-door-12-closing", None, {"tick": 60})],
            "hresin-open": [(RESIN_DOOR, "resin-door-12-open", None, {"side": "S"})],
            "idle": "resin-closed",
            "icon": [(RESIN_DOOR, "resin-door-0", None, {"fit": (44, 44)})],
        },
    },
    "sticky-resin": {
        "zoffset": GROUND_Z["sticky"],
        "sequences": {
            "idle": [("icons/Xeno/Effects.dmi", "sticky")],
            "icon": [("icons/Xeno/Effects.dmi", "sticky", None, {"fit": (44, 44)})],
        },
    },
    "evolution-tower": {
        "sequences": {
            "idle": [(XENO_2X2, "evotower")],
            "icon": [(XENO_2X2, "evotower", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "forward-hive": {
        "sequences": {
            "idle": [(XENO_2X2, "orb_idle")],
            "icon": [(XENO_2X2, "orb_idle", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    # The tunnel mouth: TGMC's hole in the ground.
    "tunnel": {
        "sequences": {
            "idle": [(XENO_FX, "hole")],
            "icon": [(XENO_FX, "hole", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "resin-trap": {
        "sequences": {
            "idle": [(WEEDS, "weednode0")],
            "icon": [(WEEDS, "weednode0", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    "maturity-tower": {
        "sequences": {
            "idle": [(XENO_2X2, "maturitytower")],
            "icon": [(XENO_2X2, "maturitytower", None, {"fit": (44, 44), "frames": (0, 1)})],
        },
    },
    # Facehugger: scuttles on its legs, and shows its leaping pose while it attacks. The embryo's host is a marine.
    "facehugger": {
        "sequences": {
            "stand": [(XENO_FX, "facehugger_inactive")],
            "run": [(XENO_FX, "facehugger")],
            "attack": [(XENO_FX, "facehugger_thrown")],
            "die": [(XENO_FX, "facehugger_dead")],
            "die-gib": "die",
            "icon": "stand:S",
        },
    },
    # Larva: TGMC draws it in one still pose per facing, so the crawl is that pose wriggling.
    "larva": {
        "sequences": {
            "stand": [(LARVA, "Larva")],
            "run": [(LARVA, "Larva Moving", None, {"bob": 4, "tick": 90})],
            "attack": "stand",
            "die": [(LARVA, "Larva Dead")],
            "die-gib": [(LARVA, "larva_gib", None, {"tick": 70})],
            "icon": "stand:S",
        },
    },
    # Infestation and evolving effects, named by the C# traits (InfestableInfo, EvolvesInfo).
    "fx-infest": {
        "sequences": {
            "burst": [(XENO_FX, "burst_stand", None, {"side": "S", "size": 64, "tick": 80})],
            "cure": [(FX32, "sparkle", None, {"size": 64, "tick": 60})],
            "evolve": [(XENO_FX, "egg exploding", None, {"size": 64, "tick": 70})],
            "devolve": [(XENO_FX, "egg opening", None, {"size": 64, "tick": 70})],
        },
    },
    # Projectile images. Weapons refer to these by name (Bullet Image:), not as actors.
    "grenade": {
        "sequences": {"idle": [(GRENADE, "grenade")]},
    },
    # The mortar and howitzer shells in flight (TGMC's ammo icons), turned to point along the arc, so they do not look like the HE grenade.
    "mortar-shell": {
        "sequences": {"idle": [(ARTILLERY, "mortar_he", None, {"facings": 16})]},
    },
    "howitzer-shell": {
        "sequences": {"idle": [(ARTILLERY, "howitzer", None, {"facings": 16})]},
    },
    # Effect images, also named by weapons (Bullet Image, CreateEffect Image). One sheet per cell size.
    # The bullet art points up, so 16 turned copies make a tracer that flies along the shot.
    # SOM weapons (TGMC's own projectile art): the red laser bolt and the plasma ball.
    "fx-laser": {
        "sequences": {
            "idle": [(PROJECTILES, "laser", None, {"facings": 16})],
            "large": [(PROJECTILES, "heavylaser", None, {"facings": 16})],
        },
    },
    "fx-plasma": {
        "sequences": {
            "idle": [(PROJECTILES, "plasma_ball_small", None, {"tick": 50})],
            "large": [(PROJECTILES, "plasma_ball_big", None, {"tick": 50})],
        },
    },
    "fx-bullet": {
        "sequences": {
            "idle": [(PROJECTILES, "bullet", None, {"facings": 16})],
            "large": [(PROJECTILES, "bullet_large", None, {"facings": 16})],
        },
    },
    # Rockets (SADAR, the mech's RPG and anti-armour missile): the art points up, so 16 turned copies fly along the shot.
    # A spent cartridge case, flung from a rifle (EjectsCasings in tgmc/code/Casings.cs); it spins by turning through the 8 facings.
    "fx-casing": {
        "sequences": {"idle": [(CASINGS, "casing", None, {"facings": 8})]},
    },
    "fx-rocket": {
        "sequences": {
            "idle": [(PROJECTILES, "rpg_he", None, {"facings": 16})],
            "large": [(PROJECTILES, "missile", None, {"facings": 16})],
        },
    },
    "fx-acid": {
        "sequences": {
            "idle": [(PROJECTILES, "xeno_acid", None, {"tick": 80})],
            "splash": [(XENO_FX, "acid_normal", None, {"tick": 60})],
            "sizzle": [(XENO_FX, "acid2", None, {"tick": 60})],
        },
    },
    # TGMC's boiler glob: a round acid ball, bigger than the small acid spit (its own sheet: another frame size than fx-acid).
    "fx-acidball": {
        "sequences": {
            "idle": [(PROJECTILES, "boiler_corrosive", None, {"tick": 80, "size": 64})],
        },
    },
    "fx-impact": {
        "sequences": {
            "spark": [(PROJECTILES, "spark", None, {"tick": 60})],
            "blood": [(XENO_FX, "splatter", None, {"swap_rg": True, "tick": 70})],
            "gore": [(XENO_FX, "splatter", None, {"tick": 70})],
            "heal": [(FX32, "sparkle", None, {"tick": 60})],
            "burst": [(FX32, "explosion", None, {"tick": 40})],
            "dust": [(FX32, "landslide_dust", None, {"tick": 70})],
            "ricochet": [(FX32, "sparks", None, {"tick": 40})],
        },
    },
    # The 65-frame TGMC explosions are a fireball that fades into smoke; every third frame at one tick each is about a second
    "fx-blast": {
        "sequences": {
            "grenade": [(FX64, "explosion", None, {"frames": (0, 65, 3), "tick": 40})],
            "small": [(FX64, "explosion", None, {"frames": (0, 40, 4), "tick": 40})],
            "fireball": [(FX64, "fireball_explosion", None, {"tick": 55})],
        },
    },
    # CAS blasts: a bomb about 8 tiles across, the MOAB about 18, with a dust cloud and a shockwave ring (fx-shockwave in sequences/misc.yaml).
    "fx-blast-cas": {
        "sequences": {"boom": [(FX96, "explosion", None, {"frames": (0, 65, 3), "tick": 40, "size": 256})]},
    },
    # A puff of dust for one tile of a spreading blast (Shockwave warhead).
    "fx-dust-tile": {
        "sequences": {"dust": [(FX32, "landslide_dust", None, {"tick": 110, "size": 96})]},
    },
    # The particles of a blast (ExplosionParticles warhead), TGMC's own: the grey smoke and the brown dust of explosions.dm, rocks and sparks.
    "fx-smoke-puff": {"sequences": {"idle": [(FX96, "smoke3", None, {"size": 96})]}},
    "fx-dirt-puff": {"sequences": {"idle": [("icons/effects/96x157.dmi", "smoke", None, {"fit": (96, 96)})]}},
    "fx-rock": {"sequences": {"idle": [("icons/effects/particles/generic_particles.dmi", "rock")]}},
    "fx-spark": {"sequences": {"idle": [(FX64, "flare", None, {"size": 14})]}},
    "fx-blast-moab": {
        "sequences": {"boom": [(FX96, "explosion", None, {"frames": (0, 65, 3), "tick": 45, "size": 576})]},
    },
    "fx-blast-moab2": {
        "sequences": {"boom": [(FX96, "explosion", None, {"frames": (0, 65, 3), "tick": 45, "size": 384})]},
    },
    "fx-dust-moab": {
        "sequences": {"dust": [(FX32, "landslide_dust", None, {"tick": 160, "size": 576})]},
    },
    "fx-blast-big": {
        "sequences": {"big": [(FX96, "explosion", None, {"frames": (0, 65, 3), "tick": 40})]},
    },
    # A mortar shell (about 5 tiles across, TGMC's 5 tile outer blast) and a howitzer shell (about 7), each with the dust
    # that hangs over the ground afterwards. One sheet per size.
    "fx-blast-mortar": {
        "sequences": {"boom": [(FX96, "explosion", None, {"frames": (0, 65, 3), "tick": 40, "size": 160})]},
    },
    "fx-blast-howi": {
        "sequences": {"boom": [(FX96, "explosion", None, {"frames": (0, 65, 3), "tick": 40, "size": 224})]},
    },
    "fx-dust-mortar": {
        "sequences": {"dust": [(FX32, "landslide_dust", None, {"tick": 120, "size": 160})]},
    },
    "fx-dust-howi": {
        "sequences": {"dust": [(FX32, "landslide_dust", None, {"tick": 120, "size": 224})]},
    },
    # Smoke that drifts off a badly damaged building (WithDamageOverlay in structures.yaml)
    "fx-smoke": {
        "sequences": {"loop": [(FX32, "smoke", None, {"side": "S", "tick": 90})]},
    },
    # Burning ground left by napalm and lasers (CAS ammo in structures.yaml)
    "fx-fire": {
        "sequences": {"burn": [(FIRE, "red_3", None, {"tick": 140})]},
    },
    # Flames the flamer leaves on the ground (the flame-patch actor in units.yaml): a looping fire that burns for several seconds.
    "flame-patch": {
        "sequences": {"idle": [(FIRE, "red_3", None, {"tick": 100})]},
    },
    # X-Napalm's patch: the same fire in blue (flame-patch-blue in units.yaml).
    "flame-patch-blue": {
        "sequences": {"idle": [(FIRE, "blue_3", None, {"tick": 100})]},
    },
    # A cloud of gas that hangs over the ground (the gas-cloud actor in units.yaml): TGMC's chemical smoke, tinted green.
    "gas-cloud": {
        "sequences": {"idle": [(CHEMSMOKE, "", (190, 255, 120), {"side": "S", "size": 128, "tick": 120})]},
    },
    # Blood on the floor where a marine is hit and while a badly hurt one walks (xenos leave green blood, fx-blood-xeno) (the Bleeds trait in tgmc/code/Blood.cs): TGMC's floor blood
    # sprites tinted red, each lying for about half a minute, drawn under the units.
    "fx-blood": {
        "zoffset": GROUND_Z["blood"],
        "sequences": {
            "small1": [(BLOOD, "mfloor1", (150, 14, 14), {"tick": 200000})],
            "small2": [(BLOOD, "mfloor2", (150, 14, 14), {"tick": 200000})],
            "small3": [(BLOOD, "mfloor3", (150, 14, 14), {"tick": 200000})],
            "small4": [(BLOOD, "mfloor4", (150, 14, 14), {"tick": 200000})],
            "small5": [(BLOOD, "mfloor5", (150, 14, 14), {"tick": 200000})],
            "small6": [(BLOOD, "mfloor6", (150, 14, 14), {"tick": 200000})],
            "small7": [(BLOOD, "mfloor7", (150, 14, 14), {"tick": 200000})],
            "big1": [(BLOOD, "splatter1", (150, 14, 14), {"tick": 220000})],
            "big2": [(BLOOD, "splatter2", (150, 14, 14), {"tick": 220000})],
            "big3": [(BLOOD, "splatter3", (150, 14, 14), {"tick": 220000})],
            "big4": [(BLOOD, "splatter4", (150, 14, 14), {"tick": 220000})],
            "big5": [(BLOOD, "splatter5", (150, 14, 14), {"tick": 220000})],
            "big6": [(BLOOD, "splatter6", (150, 14, 14), {"tick": 220000})],
        },
    },
    # Body parts thrown out of a gibbed marine (h-*, tinted red) or xeno (x-*) by the ThrowsGibs trait; each lies for over three minutes.
    "fx-gibs": {
        "zoffset": GROUND_Z["gibs"],
        "sequences": {
            "h-head": [(BLOOD, "gibhead", (170, 30, 30), {"tick": 200000})],
            "h-arm": [(BLOOD, "gibarm", (170, 30, 30), {"tick": 200000})],
            "h-leg": [(BLOOD, "gibleg", (170, 30, 30), {"tick": 200000})],
            "h-torso": [(BLOOD, "gibtorso", (170, 30, 30), {"tick": 200000})],
            "h-mid1": [(BLOOD, "gibmid1", (170, 30, 30), {"tick": 200000})],
            "h-mid2": [(BLOOD, "gibmid2", (170, 30, 30), {"tick": 200000})],
            "h-mid3": [(BLOOD, "gibmid3", (170, 30, 30), {"tick": 200000})],
            "h-up": [(BLOOD, "gibup1", (170, 30, 30), {"tick": 200000})],
            "h-down": [(BLOOD, "gibdown1", (170, 30, 30), {"tick": 200000})],
            "x-head": [(BLOOD, "xgibhead", None, {"tick": 200000})],
            "x-torso": [(BLOOD, "xgibtorso", None, {"tick": 200000})],
            "x-arm": [(BLOOD, "xgibarm", None, {"tick": 200000})],
            "x-leg": [(BLOOD, "xgibleg", None, {"tick": 200000})],
            "x-up": [(BLOOD, "xgibup1", None, {"tick": 200000})],
            "x-down": [(BLOOD, "xgibdown1", None, {"tick": 200000})],
            "x-mid1": [(BLOOD, "xgibmid1", None, {"tick": 200000})],
            "x-mid2": [(BLOOD, "xgibmid2", None, {"tick": 200000})],
            "x-mid3": [(BLOOD, "xgibmid3", None, {"tick": 200000})],
        },
    },
    # The marines' drop pod: falling with its thrusters lit, then shut on the ground (DropPodPower in tgmc/code/DropPod.cs).
    "droppod": {
        "sequences": {
            "fall": [(DROPPOD, "singlepod_green_active", None, {"tick": 100000})],
            "landed": [(DROPPOD, "singlepod_green_inactive", None, {"tick": 400000})],
        },
    },
    # The supply pod and the crate it leaves, and a smoke screen (tinted chemical smoke): see the support powers in structures.yaml.
    "supplypod": {
        "sequences": {
            "fall": [(DROPPOD, "supplypod_active", None, {"tick": 100000})],
            "landed": [(DROPPOD, "supplypod_inactive", None, {"tick": 400000})],
        },
    },
    "supply-crate": {
        "sequences": {"idle": [(DROPPOD, "supplypod_inactive", None, {"tick": 400000})]},
    },
    "smoke-cloud": {
        "sequences": {"idle": [(CHEMSMOKE, "", (225, 225, 225), {"side": "S", "size": 128, "tick": 240})]},
    },
    "fx-blood-xeno": {
        "zoffset": GROUND_Z["blood"],
        "sequences": {
            "small1": [(BLOOD, "mfloor1", (110, 210, 40), {"tick": 200000})],
            "small2": [(BLOOD, "mfloor2", (110, 210, 40), {"tick": 200000})],
            "small3": [(BLOOD, "mfloor3", (110, 210, 40), {"tick": 200000})],
            "small4": [(BLOOD, "mfloor4", (110, 210, 40), {"tick": 200000})],
            "small5": [(BLOOD, "mfloor5", (110, 210, 40), {"tick": 200000})],
            "small6": [(BLOOD, "mfloor6", (110, 210, 40), {"tick": 200000})],
            "small7": [(BLOOD, "mfloor7", (110, 210, 40), {"tick": 200000})],
            "big1": [(BLOOD, "splatter1", (110, 210, 40), {"tick": 220000})],
            "big2": [(BLOOD, "splatter2", (110, 210, 40), {"tick": 220000})],
            "big3": [(BLOOD, "splatter3", (110, 210, 40), {"tick": 220000})],
            "big4": [(BLOOD, "splatter4", (110, 210, 40), {"tick": 220000})],
            "big5": [(BLOOD, "splatter5", (110, 210, 40), {"tick": 220000})],
            "big6": [(BLOOD, "splatter6", (110, 210, 40), {"tick": 220000})],
        },
    },
    "fx-slam": {
        "sequences": {"slam": [(HEAVY_IMPACT, "heavyimpact", None, {"tick": 60})]},
    },
    "fx-slam-big": {
        "sequences": {"impact": [(FX96, "throw_impact_s", None, {"tick": 60})]},
    },
    # TGMC's weather tiles, drawn over every cell on screen by TiledWeather (Weather.cs) when the lobby's Weather option picks them.
    "fx-weather": {
        "sequences": {
            "rain": [("icons/effects/weather_effects.dmi", "rain_med", None, {"tick": 60})],
            "acidrain": [("icons/effects/weather_effects.dmi", "acid_rain", None, {"tick": 60})],
            "ash": [("icons/effects/weather_effects.dmi", "ash_storm", None, {"tick": 90})],
            "snow": [("icons/effects/weather_effects.dmi", "snow_storm", None, {"tick": 70})],
            "dust": [("icons/effects/weather_effects.dmi", "dust_med", None, {"tick": 90})],
        },
    },
    # Bloody footprints (fluidtracks.dmi, white in TGMC, which tints them with the blood colour: red for marines, acid green for
    # xenos) a badly hurt unit leaves behind (LeavesTracks in Blood.cs): boots for marines, claws for xenos.
    "fx-tracks": {
        "sequences": {
            "human1": [("icons/effects/fluidtracks.dmi", "human1", (150, 18, 18), {})],
            "human2": [("icons/effects/fluidtracks.dmi", "human2", (150, 18, 18), {})],
            "claw1": [("icons/effects/fluidtracks.dmi", "claw1", (150, 200, 40), {})],
            "claw2": [("icons/effects/fluidtracks.dmi", "claw2", (150, 200, 40), {})],
        },
    },
    # Bullet holes punched in a structure a bullet hits (bulletholes.dmi), and the holes acid eats in one (new_acid.dmi).
    "fx-hole": {
        "sequences": {
            "bullet1": [("icons/effects/bulletholes.dmi", "bhole_1_1", None, {})],
            "bullet2": [("icons/effects/bulletholes.dmi", "bhole_1_5", None, {})],
            "bullet3": [("icons/effects/bulletholes.dmi", "bhole_1_9", None, {})],
            "bullet4": [("icons/effects/bulletholes.dmi", "bhole_1_14", None, {})],
            "acid1": [("icons/effects/new_acid.dmi", "hole_0", None, {})],
            "acid2": [("icons/effects/new_acid.dmi", "hole_1", None, {})],
        },
    },
    # Ground warnings (Telegraph in Weather.cs): where an orbital strike or a boiler glob will land, and where a drop pod comes down.
    "fx-telegraph": {
        "sequences": {"box": [("icons/effects/telegraph_96x96.dmi", "target_largebox", None, {"size": 96})]},
    },
    "fx-marker": {
        "sequences": {
            "xeno": [("icons/effects/xeno_target.dmi", "all", None, {"size": 64})],
            "pod": [("icons/effects/supplypod_down_target.dmi", "all", None, {"size": 64})],
        },
    },
    # The heat bar over a machine gun that has been firing a long burst (overheat.dmi).
    "fx-overheat": {
        "sequences": {"bar": [("icons/effects/overheat.dmi", "status_bar", (255, 110, 30), {})]},
    },
    # A runner's claw swipe, drawn over whatever it hits (the runner has no attack frames of its own in TGMC)
    "fx-claw": {
        "sequences": {"slash": [(FX32, "claw", None, {"tick": 60})]},
    },
}


def team_layer(layer, rgb):
    """The layer with a team tint, unless it already has its own. Layers are (dmi, state[, tint[, options]])."""
    if len(layer) == 2:
        return layer + (rgb,)
    if layer[2] is None:
        return (layer[0], layer[1], rgb) + tuple(layer[3:])
    return layer


# Every xeno caste has a curled-up and a knocked-flat picture in TGMC ("<Caste> Sleeping", "<Caste> Knocked Down", one view each):
# rest, for a hurt xeno lying idle on weeds, and down, for a stunned one (WithInfantryBody@rest and @down on ^Xeno).
for _unit in UNITS.values():
    _seqs = _unit["sequences"]
    _pose = _seqs.get("stand") or _seqs.get("walk")
    while isinstance(_pose, str):
        _pose = _seqs.get(_pose.partition(":")[0].partition("#")[0])
    if _pose and _pose[0][1].endswith(" Walking"):
        _caste = _pose[0][1][:-len(" Walking")]
        _seqs.setdefault("rest", [(_pose[0][0], f"{_caste} Sleeping")])
        _seqs.setdefault("down", [(_pose[0][0], f"{_caste} Knocked Down")])
# These three have no such pictures: they stay as they stand.
for _name in ("facehugger", "larva", "puppet"):
    UNITS[_name]["sequences"].setdefault("rest", "stand")
    UNITS[_name]["sequences"].setdefault("down", "stand")

# Xeno units take the xeno team colour on every layer
# A marine that dies topples over rather than becoming a husk: any unit whose stand is the marine stack and die is still the husk.
for _unit in UNITS.values():
    _seqs = _unit["sequences"]
    if _seqs.get("die") == [(HUMAN, "husk")] and isinstance(_seqs.get("stand"), list) and _seqs["stand"][0][1] == "body_m":
        _seqs["die"] = fallen(_seqs["stand"])
        # The same pose, held: a marine knocked flat by a facehugger lies on his side until it lets go.
        _first = _seqs["stand"][0]
        _seqs["down"] = [(_first[0], _first[1], None, {**(_first[3] if len(_first) > 3 else {}), "fall": 6, "last": True})] + _seqs["stand"][1:]

XENO_UNITS = ["runner", "hunter", "sentinel", "drone", "warrior", "queen", "facehugger", "larva"] + ["baneling", "beetle", "defender", "dragon", "gorger", "hivelord", "king", "mantis", "nymph", "puppeteer", "puppet", "pyrogen", "scorpion"] + ["spitter", "praetorian", "crusher", "ravager", "defiler", "boiler", "carrier", "warlock", "shrike", "widow", "wraith", "bull", "behemoth"]
for _unit in XENO_UNITS:
    _seqs = UNITS[_unit]["sequences"]
    for _name, _value in _seqs.items():
        if isinstance(_value, list):
            _seqs[_name] = [team_layer(layer, XENO_TEAM) for layer in _value]


def tinted(img, rgb):
    """Multiply the colour channels by rgb/255 and keep the alpha."""
    if rgb is None or rgb == CLOTH:
        return img
    r, g, b, a = img.split()
    out = ImageChops.multiply(Image.merge("RGB", (r, g, b)), Image.new("RGB", img.size, rgb))
    out.putalpha(a)
    return out


def _opaque(frames):
    return sum(1 for img in frames for a in img.getchannel("A").getdata() if a)


def _layer_images(dmi, state, tint=None, opts=None):
    """Return {side: [frame images]} for S/N/E/W, {"*": [frame images]} for a 1-dir state, or, with the "facings"
    option, {0..facings-1: [frame images]} for a 1-dir state turned to each facing (facing 0 points north).
    With "or_sheet" (a second .dmi with the same state) each side comes from whichever sheet shows more of the gun there: a two-handed
    gun is one gun, in the hand that holds it toward the viewer, not one in each hand."""
    opts = opts or {}
    if "or_sheet" in opts:
        rest = {k: v for k, v in opts.items() if k != "or_sheet"}
        first = _layer_images(dmi, state, tint, rest)
        second = _layer_images(opts["or_sheet"], state, tint, rest)
        merged = {}
        for k in first:
            better = second[k] if _opaque(second[k]) > _opaque(first[k]) else first[k]
            merged[k] = better
        return merged
    frames = dmi.frames(state)
    if "by_side" in opts:  # each side from its own 4-direction state, that state's own view of that side (a vehicle part drawn per hull direction)
        return {side: [tinted(fr[tgmc_dmi.DIRS4.index(side)], tint) for fr in dmi.frames(opts["by_side"][side])] for side in tgmc_dmi.DIRS4}
    if "frames" in opts:
        frames = frames[slice(*opts["frames"])]
    dirs = dmi.state(state)["dirs"]
    if dirs in (1, 8) and "facings" in opts:  # an 8-dir state is turned from its first (south) direction too
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
    pad = (opts or {}).get("pad")
    if pad:  # centre on a transparent canvas of this size, feet at the bottom: layers from different sheets then line up
        def padded(img):
            canvas = Image.new("RGBA", tuple(pad), (0, 0, 0, 0))
            canvas.alpha_composite(img.convert("RGBA"), ((pad[0] - img.width) // 2, pad[1] - img.height))
            return canvas
        sides = {k: [padded(img) for img in frames] for k, frames in sides.items()}
    centre = (opts or {}).get("centre")
    if centre:  # centre on a transparent canvas of this size, so a 32px body lines up under a 64px in-hand gun
        sides = {k: [pad_to(img, centre) for img in frames] for k, frames in sides.items()}
    scale = (opts or {}).get("scale")
    if scale:
        sides = {k: [img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS) for img in frames]
                 for k, frames in sides.items()}
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


def cloth_grey(img):
    """A cloth layer as light grey, so the player colour multiplied over it reads as that colour and not as a dark mud."""
    grey = img.convert("L").point(lambda v: 90 + round(165 * (v / 255) ** 0.5))
    return Image.merge("RGBA", (grey, grey, grey, img.getchannel("A")))


def composite(layers, cloth=None):
    """layers: list of (dmi, state, sides) -> {side or '*': [composited frames]}.
    With `cloth` (one flag a layer) only the flagged layers are drawn, in grey, and every other layer cuts its shape out of them."""
    names = set(k for _, _, sides in layers for k in sides)
    out = {}
    for name in names:
        frame_count = len(layers[0][2][name])
        stacked = []
        for f in range(frame_count):
            base = None
            for i, (dmi, state, sides) in enumerate(layers):
                img = sides[name][f]
                if cloth:
                    if base is None:
                        base = Image.new("RGBA", img.size, (0, 0, 0, 0))
                    if img.size != base.size:
                        raise SystemExit(f"{dmi.path}:{state} is {img.size}, base is {base.size}")
                    if cloth[i]:
                        base = Image.alpha_composite(base, cloth_grey(img))
                    else:
                        base.putalpha(ImageChops.subtract(base.getchannel("A"), img.getchannel("A")))
                elif base is None:
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


def fall_frames(img, count):
    """`count` copies of img turning clockwise from upright to lying on its side (90 degrees), the last one held."""
    return [img.rotate(-90 * i / (count - 1), resample=Image.BICUBIC) for i in range(count)]


def bob_frames(img, count, height=3, tilt=8):
    """`count` copies of img hopping and wriggling in a loop: it rises and falls once and tilts both ways."""
    frames = []
    for i in range(count):
        lift = round(height * math.sin(math.pi * i / count))
        turned = img.rotate(tilt * math.sin(2 * math.pi * i / count), resample=Image.BICUBIC)
        cell = Image.new("RGBA", img.size, (0, 0, 0, 0))
        cell.paste(turned, (0, -lift), turned)
        frames.append(cell)
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


def render_sequences(tgmc, sequences, cell=None, cloth=False):
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
        def options(spec):
            opts = spec[3] if len(spec) > 3 else None
            if opts and isinstance(opts.get("or_sheet"), str):  # the second sheet of a two-handed gun, loaded here
                opts = dict(opts, or_sheet=tgmc_dmi.Dmi(os.path.join(tgmc, opts["or_sheet"])))
            return opts

        layers = [(dmi, state, layer_images(dmi, state, spec[2] if len(spec) > 2 else None, options(spec)))
                  for (dmi, state), spec in zip(dmis, layer_specs)]
        sides = composite(layers, [len(spec) > 2 and spec[2] == CLOTH for spec in layer_specs] if cloth else None)
        first_opts = layer_specs[0][3] if len(layer_specs[0]) > 3 else {}
        if "fade" in first_opts:  # a still pose that fades out over N frames
            sides = {k: fade_frames(frames[0], first_opts["fade"]) for k, frames in sides.items()}
        if "fall" in first_opts:  # a still pose that topples onto its side over N frames
            sides = {k: fall_frames(frames[0], first_opts["fall"]) for k, frames in sides.items()}
        if first_opts.get("last"):  # keep only the final frame, for a pose held after its animation
            sides = {k: frames[-1:] for k, frames in sides.items()}
        if "bob" in first_opts:  # a still pose that hops and wriggles over N frames, for a crawl
            sides = {k: bob_frames(frames[0], first_opts["bob"]) for k, frames in sides.items()}
        size = (dmis[0][0].icon_w, dmis[0][0].icon_h)
        if "pad" in first_opts:
            factor = first_opts.get("scale", 1)
            size = (round(first_opts["pad"][0] * factor), round(first_opts["pad"][1] * factor))
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


SHADOW_PAD = 8  # a shadow cell is the unit's cell with this much room on every side: feet stand on the cell's bottom edge


def ground_shadow(cell):
    """A soft dark ellipse on the ground under the lowest part of `cell`'s figure, as wide as what stands there."""
    out = Image.new("RGBA", (cell.width + 2 * SHADOW_PAD, cell.height + 2 * SHADOW_PAD), (0, 0, 0, 0))
    solid = cell.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    box = solid.getbbox()
    if box is None:
        return out
    left, top, right, bottom = box
    band = max(4, round((bottom - top) * 0.15))
    feet = solid.crop((left, bottom - band, right, bottom)).getbbox()
    w = max(14, feet[2] - feet[0] + 6)
    h = min(14, max(6, w * 0.35))
    cx, cy = left + (feet[0] + feet[2]) / 2 + SHADOW_PAD, bottom - 2 + SHADOW_PAD
    big = Image.new("L", (out.width * 4, out.height * 4), 0)
    ImageDraw.Draw(big).ellipse([(cx - w / 2) * 4, (cy - h / 2) * 4, (cx + w / 2) * 4, (cy + h / 2) * 4], fill=150)
    out.putalpha(big.filter(ImageFilter.GaussianBlur(6)).resize(out.size, Image.LANCZOS))
    return out


ICON_W, ICON_H = 62, 46   # the production palette's cell
# Marine cards wear the HUD's tgui charcoal (see make_chrome.py); xeno cards stay purple.
CAMEO_TONES = {"marine": ((58, 62, 70), (26, 27, 30)), "xeno": ((72, 44, 84), (28, 16, 36))}


def cameo(img, tone="marine", bust=False):
    """A palette icon: the sprite trimmed, scaled up in whole steps (crisp pixel art) or smoothly down, outlined so it stands out,
    on a dark card with a vignette and the HUD's charcoal frame. bust keeps only the top of a standing figure (head and shoulders)."""
    img = img.convert("RGBA")
    box = img.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox()
    if box:
        img = img.crop(box)
    if bust and img.height > img.width:
        img = img.crop((0, 0, img.width, max(10, round(img.height * 0.7))))
    room_w, room_h = ICON_W - 8, ICON_H - 8
    scale = min(room_w / img.width, room_h / img.height)
    if scale >= 1:
        scale = int(scale)
        img = tgmc_dmi.nearest(img, (img.width * scale, img.height * scale))
    else:
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    top, bottom = CAMEO_TONES[tone]
    card = Image.new("RGBA", (ICON_W, ICON_H))
    d = ImageDraw.Draw(card)
    for y in range(ICON_H):
        t = y / (ICON_H - 1)
        d.line([(0, y), (ICON_W, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,))
    vignette = Image.new("L", (ICON_W, ICON_H), 0)
    ImageDraw.Draw(vignette).ellipse([-ICON_W // 4, -ICON_H // 4, ICON_W * 5 // 4, ICON_H * 5 // 4], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(10))
    card = Image.composite(card, Image.new("RGBA", card.size, (14, 14, 16, 255)), vignette)
    x, y = (ICON_W - img.width) // 2, (ICON_H - img.height) // 2
    shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    mask = img.getchannel("A").point(lambda a: 255 if a > 40 else 0)
    outline = Image.new("L", card.size, 0)
    outline.paste(mask, (x, y))
    outline = outline.filter(ImageFilter.MaxFilter(3))
    shadow.paste((8, 9, 6, 255), (0, 0), outline)
    card.alpha_composite(shadow)
    card.alpha_composite(img, (x, y))
    d = ImageDraw.Draw(card)
    d.rectangle([1, 1, ICON_W - 2, ICON_H - 2], outline=(70, 74, 82, 255))
    d.rectangle([0, 0, ICON_W - 1, ICON_H - 1], outline=(16, 16, 16, 255))
    return card


def icon_look(layer_specs):
    """(tone, bust) for the layers an icon is drawn from: xeno art on purple, a human figure as a head-and-shoulders bust."""
    files = [spec[0] for spec in layer_specs]
    return ("xeno" if any("Xeno" in f for f in files) else "marine"), any(f == HUMAN for f in files)


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
        # No "fit" here: cameo() scales from the full-size art.
        raw = [(sp[0], sp[1], sp[2] if len(sp) > 2 else None, {k: v for k, v in (sp[3] if len(sp) > 3 else {}).items() if k != "fit"})
               for sp in icon_spec]
        icon_cells, icon_size, icon_defs, _ = render_sequences(tgmc, {"icon": raw})
        tone, bust = icon_look(icon_spec)
        icon_cells = [cameo(c, tone, bust) for c in icon_cells]
        icon_size = (ICON_W, ICON_H)

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
    if isinstance(icon_spec, str):  # an icon that is a still of the unit itself: it too gets a cameo card, on its own sheet
        layers = spec["sequences"][icon_spec.partition(":")[0].partition("#")[0]]
        while isinstance(layers, str):
            layers = spec["sequences"][layers.partition(":")[0].partition("#")[0]]
        icon_cells = [cameo(sheet_cells[starts["icon"][0]], *icon_look(layers))]
        icon_size = (ICON_W, ICON_H)
        icon_defs = [("icon", 0, 1, 1, None, None)]
        seq_defs = [d for d in seq_defs if d[0] != "icon"]

    cw, ch = cell_size
    os.makedirs(os.path.join(out_dir, "sequences"), exist_ok=True)
    save_sheet(sheet_cells, cell_size, os.path.join(out_dir, "sprites", f"{unit}.png"))
    has_cloth = any(len(layer) > 2 and layer[2] == CLOTH for v in main.values() if isinstance(v, list) for layer in v)
    if has_cloth:
        cloth_cells = render_sequences(tgmc, main, spec.get("cell"), cloth=True)[0]
        assert len(cloth_cells) == len(sheet_cells), unit
        save_sheet(cloth_cells, cell_size, os.path.join(out_dir, "sprites", f"{unit}-cloth.png"))
    if icon_cells is not None:
        save_sheet(icon_cells, icon_size, os.path.join(out_dir, "sprites", f"{unit}-icon.png"))

    lines = ["# Generated by mod/build_sprites.py from TGMC art. Do not edit.",
             f"{unit}:", "\tDefaults:", f"\t\tFilename: sprites/{unit}.png"]
    if "zoffset" in spec:
        lines.append(f"\t\tZOffset: {spec['zoffset']}")
    for seq_name, start, length, facings, tick, stride in seq_defs:
        lines.append(f"\t{seq_name}:")
        lines.append(f"\t\tStart: {start}")
        if length != 1:
            lines.append(f"\t\tLength: {length}")
        if facings != 1:
            # OpenRA's facing angle grows counter-clockwise from north; the sheets are laid out clockwise, so reverse them.
            lines.append(f"\t\tFacings: -{facings}")
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
    # A unit that turns gets a shadow for each facing, placed under that view's feet (WithIdleOverlay@shadow on ^Unit).
    pose = next((n for n in ("stand", "idle") if n in starts and starts[n][2] > 1), None)
    if pose:
        start, length, facings, _, stride = starts[pose]
        save_sheet([ground_shadow(sheet_cells[start + i * (stride or length)]) for i in range(facings)],
                   (cw + 2 * SHADOW_PAD, ch + 2 * SHADOW_PAD), os.path.join(out_dir, "sprites", f"{unit}-shadow.png"))
        lines += ["\tshadow:", f"\t\tFilename: sprites/{unit}-shadow.png", "\t\tStart: 0", f"\t\tFacings: -{facings}", f"\t\tZOffset: {GROUND_Z['shadow']}"]
    if has_cloth:  # the same cells on the cloth sheet
        lines += [f"{unit}-cloth:", f"\tInherits: {unit}", "\tDefaults:", f"\t\tFilename: sprites/{unit}-cloth.png"]
    with open(os.path.join(out_dir, "sequences", f"{unit}.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    return {"unit": unit, "sheet": f"sprites/{unit}.png", "cell": [cw, ch], "cells": len(sheet_cells),
            "sequences": [{"name": n, "start": s, "length": l, "facings": fa, "tick": t} for n, s, l, fa, t, _ in seq_defs]}


# The Condor, TGMC's CAS jet. It is no single sprite: the jet is a jigsaw of 32px tiles laid out by _maps/shuttles/casplane.dmm,
# each tile a turf or structure whose icon state is set in cas_plane_parts.dm. compose_condor reads both and puts the jet
# back together, nose up. build_condor then turns it into 16 facings and 16 shadow cells for the CAS strike's flyby.
CONDOR_FILES = ["icons/turf/cas.dmi", "icons/obj/structures/cas_cockpit.dmi", "_maps/shuttles/casplane.dmm",
                "code/game/objects/structures/cas_plane_parts.dm"]


# The Alamo, the dropship that lands for the Evac mission: its layout, read like the Condor's (see compose_alamo).
ALAMO_FILES = ["_maps/shuttles/alamo.dmm", "_maps/shuttles/minidropship_standard.dmm"]


def compose_condor(tgmc):
    import re
    read = lambda rel: open(os.path.join(tgmc, rel), encoding="utf-8").read()
    parts, dmm = read(CONDOR_FILES[3]), read(CONDOR_FILES[2])

    states, overlays, current = {}, {}, None
    for line in parts.splitlines():
        m = re.match(r"^(/(?:turf|obj)/[\w/]+)\s*$", line)
        if m:
            current = m.group(1)
            continue
        m = re.match(r'^\s+icon_state = "([^"]+)"', line)
        if m and current:
            states.setdefault(current, m.group(1))
    current = None
    for line in parts.splitlines():
        m = re.match(r"^(/(?:turf|obj)/[\w/]+)/Initialize", line)
        if m:
            current = m.group(1)
            overlays.setdefault(current, [])
            continue
        m = re.search(r"image\('icons/turf/cas.dmi', src, \"([^\"]+)\"", line)
        if m and current:
            overlays[current].append([m.group(1), 0, 0])
            continue
        m = re.search(r"overlay\.pixel_([xy]) = (-?\d+)", line)
        if m and current and overlays.get(current):
            overlays[current][-1][1 if m.group(1) == "x" else 2] = int(m.group(2))

    keys, key, buf = {}, None, []
    for line in dmm.splitlines():
        m = re.match(r'^"(\w+)" = \($', line)
        if m:
            key, buf = m.group(1), []
            continue
        if key:
            buf.append(line)
            if line.startswith("/area") and line.rstrip().endswith(")"):
                items = []
                for typ, attrs in re.findall(r"(/(?:turf|obj)/[\w/]+)(\{[^}]*\})?", "\n".join(buf)):
                    d = re.search(r"dir = (\d+)", attrs)
                    items.append((typ, int(d.group(1)) if d else 2))
                keys[key], key = items, None
    columns = {int(m.group(1)): m.group(4).split("\n")
               for m in re.finditer(r'^\((\d+),(\d+),(\d+)\) = \{"\n(.*?)\n"\}', dmm, re.S | re.M)}
    width, height = max(columns), len(columns[1])

    cas = tgmc_dmi.Dmi(os.path.join(tgmc, CONDOR_FILES[0]))
    dir_index = {2: 0, 1: 1, 4: 2, 8: 3}   # TGMC's S, N, E, W

    def tile(state, direction):
        if not cas.has_state(state):
            return None
        index = dir_index.get(direction, 0) if cas.state(state)["dirs"] >= 4 else 0
        return cas.frames(state)[0][index]

    canvas = Image.new("RGBA", (width * 32 + 96, height * 32 + 96), (0, 0, 0, 0))

    def put(img, x, y):
        if img is not None:
            canvas.alpha_composite(img.convert("RGBA"), (x + 48, y + 48))

    skip = ("/turf/open", "template_noop", "attach_point", "docking", "telecomms")
    for x in range(1, width + 1):
        for row, tile_key in enumerate(columns[x]):
            for typ, direction in keys.get(tile_key, []):
                if any(s in typ for s in skip):
                    continue
                alt = typ.replace("/obj/structure/caspart", "/turf/closed/shuttle/cas")
                state = states.get(typ) or states.get(alt)
                if state is None:
                    continue   # the pilot's chair: hidden under the canopy anyway
                px, py = (x - 1) * 32, row * 32
                put(tile(state, direction), px, py)
                for name, dx, dy in overlays.get(typ, []) + overlays.get(alt, []):
                    put(tile(name, 2), px + dx, py - dy)
    canopy = tgmc_dmi.Dmi(os.path.join(tgmc, CONDOR_FILES[1])).frames("cockpit_closed")[0][0]
    put(canopy, 5 * 32 - 16, 32)
    return canvas.crop(canvas.getbbox())


def compose_alamo(tgmc, layout=ALAMO_FILES[0]):
    """A dropship from TGMC's own layout (the Alamo's _maps/shuttles/alamo.dmm by default), one map cell per 32 px tile: (hull, doors), where hull is the ship
    with its doors left out and doors maps each door state (door_closed, door_opening, door_open, door_closing) to a list of frames the
    size of the hull, holding only the side hatches, the rear ramp and the cockpit hatch. The transit shutters are left out: they close
    only in flight."""
    import re
    import tgmc_objects
    tgmc_objects.load(tgmc)
    text = open(os.path.join(tgmc, layout), encoding="utf-8").read()
    keys = {}
    # The last key is followed by the grid, not by another key: a blank line ends it.
    for m in re.finditer(r'^"(\w+)" = \(\n(.*?)\)\n(?="|\n)', text + '"', re.S | re.M):
        items = []
        for e in re.finditer(r"(?m)^(/[\w/]+)(\{.*?\n\t\}|\{[^\n]*\})?", m.group(2), re.S):
            items.append((e.group(1), dict((k, v.strip().rstrip(",;")) for k, v in re.findall(r"(\w+)\s*=\s*([^;\n]+)", e.group(2) or ""))))
        keys[m.group(1)] = items
    columns = {int(m.group(1)): m.group(4).split("\n")
               for m in re.finditer(r'^\((\d+),(\d+),(\d+)\) = \{"\n(.*?)\n"\}', text, re.S | re.M) if m.group(3) == "1"}
    width, height = max(columns), len(columns[1])
    sheets = {}

    def sheet(icon):
        if icon not in sheets:
            path = os.path.join(tgmc, icon)
            sheets[icon] = tgmc_dmi.Dmi(path) if os.path.exists(path) else None
        return sheets[icon]

    def text_of(v):
        m = re.match(r"""^['"](.*)['"]$""", v or "")
        return m.group(1) if m else None

    dir_index = {2: 0, 1: 1, 4: 2, 8: 3}   # TGMC's S, N, E, W
    named_dirs = {"NORTH": 1, "SOUTH": 2, "EAST": 4, "WEST": 8}
    skip = ("/area", "/turf/template_noop", "/turf/open/space", "/obj/machinery/telecomms", "/obj/docking_port", "/obj/effect/landmark",
            "/obj/machinery/door/poddoor/shutters/transit")
    hull = Image.new("RGBA", (width * 32, height * 32), (0, 0, 0, 0))

    # A piece may hang off the map's edge (the Tadpole's nose sits 32 px north of its first row): what falls outside is cut.
    def put(img, px, py):
        piece = Image.new("RGBA", hull.size, (0, 0, 0, 0))
        piece.paste(img, (px, py))
        hull.alpha_composite(piece)

    door_states = ("door_closed", "door_opening", "door_open", "door_closing")
    placed_doors = []   # (Dmi, direction index, x, y)
    for x in range(1, width + 1):
        for row, key in enumerate(columns[x]):
            # A map key lists its objects before its turf: the floor goes down first, or it covers the hull pieces standing on it.
            for typ, attrs in sorted(keys.get(key, []), key=lambda e: not e[0].startswith("/turf")):
                if typ.startswith(skip):
                    continue
                r = tgmc_objects.resolve(typ)
                d = sheet(text_of(attrs.get("icon")) or text_of(r.get("icon")) or "")
                state = text_of(attrs.get("icon_state")) or text_of(r.get("icon_state"))
                if d is None or state is None:
                    continue
                raw_dir = attrs.get("dir") or r.get("dir") or "2"
                direction = int(raw_dir) if raw_dir.isdigit() else named_dirs.get(raw_dir, 2)
                index = dir_index.get(direction, 0)
                if typ.startswith("/obj/machinery/door/airlock"):
                    if all(d.has_state(st) for st in door_states):
                        placed_doors.append((d, index, (x - 1) * 32, row * 32))
                    continue
                if not d.has_state(state):
                    continue
                dirs = d.state(state)["dirs"]
                img = d.frames(state)[0][min(index, dirs - 1) if dirs > 1 else 0].convert("RGBA")
                px = int(attrs.get("pixel_x") or r.get("pixel_x") or 0)
                py = int(attrs.get("pixel_y") or r.get("pixel_y") or 0)
                put(img, (x - 1) * 32 + px, row * 32 + 32 - img.height - py)

    doors = {}
    for st in door_states if placed_doors else ():   # the Tadpole has no airlocks
        count = max(len(d.frames(st)) for d, _, _, _ in placed_doors)
        frames = []
        for i in range(count):
            frame = Image.new("RGBA", hull.size, (0, 0, 0, 0))
            for d, index, px, py in placed_doors:
                seq = d.frames(st)
                dirs = d.state(st)["dirs"]
                img = seq[min(i, len(seq) - 1)][min(index, dirs - 1) if dirs > 1 else 0].convert("RGBA")
                frame.alpha_composite(img, (px, py + 32 - img.height))
            frames.append(frame)
        doors[st] = frames
    return hull, doors


def build_alamo(tgmc, out_dir, name="alamo", layout=ALAMO_FILES[0]):
    """sprites/<name>.png: the hull, its shadow, then the door frames, each the hull's size. Sequences: idle, shadow, doors-closed,
    doors-opening, doors-open, doors-closing (a ship with no airlocks, the Tadpole, has idle and shadow only)."""
    hull, doors = compose_alamo(tgmc, layout)
    r, g, b, a = hull.split()
    shadow = Image.merge("RGBA", (r.point(lambda v: 0), g.point(lambda v: 0), b.point(lambda v: 0), a.point(lambda v: round(v * 0.4))))
    cells, starts = [hull, shadow], {}
    for st in doors:
        starts[st] = len(cells)
        cells.extend(doors[st])
    save_sheet(cells, hull.size, os.path.join(out_dir, "sprites", f"{name}.png"))
    lines = [f"# Generated by mod/build_sprites.py from TGMC art ({layout}). Do not edit.", f"{name}:", "\tDefaults:",
             f"\t\tFilename: sprites/{name}.png", "\tidle:", "\t\tStart: 0", "\tshadow:", "\t\tStart: 1"]
    for st in doors:
        seq = st.replace("door_", "doors-")
        lines += [f"\t{seq}:", f"\t\tStart: {starts[st]}", f"\t\tLength: {len(doors[st])}", "\t\tTick: 100"]
    with open(os.path.join(out_dir, "sequences", f"{name}.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return {"unit": name, "sheet": f"sprites/{name}.png", "cell": list(hull.size), "cells": len(cells)}


def build_condor(tgmc, out_dir, scale=0.5, facings=16):
    import math
    jet = compose_condor(tgmc)
    jet = jet.resize((max(1, round(jet.width * scale)), max(1, round(jet.height * scale))), Image.LANCZOS)
    cell = int(math.ceil(math.hypot(jet.width, jet.height) / 2) * 2) + 2
    cells, shadows = [], []
    for i in range(facings):
        turned = jet.rotate(-i * 360 / facings, resample=Image.BICUBIC, expand=True)
        frame = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
        frame.paste(turned, ((cell - turned.width) // 2, (cell - turned.height) // 2), turned)
        cells.append(frame)
        r, g, b, a = frame.split()
        shadows.append(Image.merge("RGBA", (r.point(lambda v: 0), g.point(lambda v: 0), b.point(lambda v: 0),
                                            a.point(lambda v: round(v * 0.35)))))
    save_sheet(cells + shadows, (cell, cell), os.path.join(out_dir, "sprites", "condor.png"))
    lines = ["# Generated by mod/build_sprites.py from TGMC art. Do not edit.", "condor:", "\tDefaults:",
             "\t\tFilename: sprites/condor.png", "\tidle:", "\t\tStart: 0", f"\t\tFacings: -{facings}",
             "\tshadow:", f"\t\tStart: {facings}", f"\t\tFacings: -{facings}"]
    os.makedirs(os.path.join(out_dir, "sequences"), exist_ok=True)
    with open(os.path.join(out_dir, "sequences", "condor.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return {"unit": "condor", "sheet": "sprites/condor.png", "cell": [cell, cell], "cells": len(cells) + len(shadows)}


# TGMC's tank gun overlay sits this far from the turret's corner (/atom/movable/vis_obj/tank_gun: pixel_x -70, pixel_y -69).
TANK_GUN_OFFSET = (-70, -69)


def build_vehicle_turret(tgmc, unit, spec, out_dir):
    """sprites/<unit>.png: the turret of a vehicle, one cell per facing, on a canvas the size of the gun sheet centred on the hull.
    BYOND anchors pictures at their bottom-left corner: the turret body's corner is the hull's, and the cannon's is TANK_GUN_OFFSET from it.
    Each TGMC view is the turret pointing that way, whatever the hull does, so it turns freely over the hull (WithSpriteTurret)."""
    vt = spec["vehicle_turret"]
    hull = tgmc_dmi.Dmi(os.path.join(tgmc, vt["hull"][0]))
    gun = tgmc_dmi.Dmi(os.path.join(tgmc, vt["gun"]))
    size = gun.icon_w
    corner = ((size - hull.icon_w) // 2, (size + hull.icon_h) // 2)  # the hull's bottom-left corner on the canvas
    sides = {}
    for d, side in enumerate(tgmc_dmi.DIRS4):
        cell = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        if vt.get("with_hull"):
            h = hull.frames(vt["hull"][1])[0][d]
            cell.paste(h, ((size - hull.icon_w) // 2, (size - hull.icon_h) // 2), h)
        if vt["body"]:
            body = gun.frames(vt["body"])[0][d]
            cell.paste(body, (corner[0], corner[1] - gun.icon_h), body)
        cannon = gun.frames(vt["cannon"])[0][d]
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        layer.paste(cannon, (corner[0] + TANK_GUN_OFFSET[0], corner[1] - TANK_GUN_OFFSET[1] - gun.icon_h), cannon)
        cell.alpha_composite(layer)
        sides[side] = cell
    cells = [sides[FACING_SOURCE[name]] for name in FACING_NAMES]
    save_sheet(cells, (size, size), os.path.join(out_dir, "sprites", f"{unit}.png"))
    os.makedirs(os.path.join(out_dir, "sequences"), exist_ok=True)
    with open(os.path.join(out_dir, "sequences", f"{unit}.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(["# Generated by mod/build_sprites.py from TGMC art. Do not edit.", f"{unit}:", "\tDefaults:",
                           f"\t\tFilename: sprites/{unit}.png", f"\t{vt.get('sequence', 'turret')}:", "\t\tStart: 0", f"\t\tFacings: -{len(cells)}"]) + "\n")
    return {"unit": unit, "sheet": f"sprites/{unit}.png", "cell": [size, size], "cells": len(cells),
            "sequences": [{"name": vt.get("sequence", "turret"), "start": 0, "length": 1, "facings": len(cells), "tick": None}]}


def merge_turret(out_dir, hull, turret):
    seq_dir = os.path.join(out_dir, "sequences")
    lines = open(os.path.join(seq_dir, f"{turret}.yaml"), encoding="utf-8").read().splitlines()
    filename = next(l.split(":", 1)[1].strip() for l in lines if l.strip().startswith("Filename:"))
    body = []
    for line in lines[3:]:
        if line.startswith("\tDefaults:") or line.strip().startswith("Filename:"):
            continue
        body.append(line)
        if line.startswith("\t") and not line.startswith("\t\t") and line.endswith(":"):
            body.append(f"\t\tFilename: {filename}")
    with open(os.path.join(seq_dir, f"{hull}.yaml"), "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(body) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", required=True, help="path to a terragov-marine-corps checkout")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "mod", "tgmc"))
    ap.add_argument("--units", nargs="*", default=sorted(UNITS) + ["condor", "alamo", "tadpole"])
    args = ap.parse_args()

    report = []
    for unit in args.units:
        info = (build_condor(args.tgmc, args.out) if unit == "condor" else build_alamo(args.tgmc, args.out) if unit == "alamo"
                else build_alamo(args.tgmc, args.out, "tadpole", ALAMO_FILES[1]) if unit == "tadpole"
                else build_vehicle_turret(args.tgmc, unit, UNITS[unit], args.out) if "vehicle_turret" in UNITS.get(unit, {})
                else build_unit(args.tgmc, unit, UNITS[unit], args.out))
        report.append(info)
        print(f"{unit}: {info['cells']} cells of {info['cell'][0]}x{info['cell'][1]}px -> {info['sheet']}")
        # A vehicle's turret has its own sheet (another frame size than the hull), but the turret trait reads the hull's image:
        # copy the turret's sequences into the hull's sequence file, each with its own Filename.
        if unit.endswith("-turret") and unit[:-len("-turret")] in args.units:
            merge_turret(args.out, unit[:-len("-turret")], unit)
    with open(os.path.join(args.out, "sprites.json"), "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
