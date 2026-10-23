"""Which TGMC picture each object of a TGMC .dmm map shows, so the converted maps carry their furniture, plants, decals and barricades.

Like tgmc_turfs.py for turfs: object paths are defined in DM code (code/game/objects and a few other directories) with an `icon` sheet and
an `icon_state`, inherited down the path. An object in a map may override icon_state and dir. Objects with no picture of their own (landmarks,
cables, pipes, spawners) and anything that is not part of the scenery are skipped.

layers(path, vars, states) returns [(sheet, state, dir)] for one object, or [].
"""
import os
import re

DEFS = {}
_loaded = []

# Never drawn: markers and hidden infrastructure, moving things, loose items.
SKIP = ("/obj/effect/landmark", "/obj/effect/ai_node", "/obj/effect/spawner", "/obj/structure/cable", "/obj/machinery/atmospherics",
        "/obj/structure/disposalpipe", "/obj/machinery/miner", "/obj/effect/step_trigger", "/obj/effect/forcefield",
        "/mob/", "/obj/effect/alien", "/obj/structure/xeno", "/obj/effect/temp", "/obj/machinery/camera", "/obj/machinery/power/apc",
        "/obj/effect/abstract",
        # The poddoors that wall in the landing zone (TGMC opens them on a timer) and their buttons; the RTS has no use for them.
        "/obj/machinery/door/poddoor/timed_late/containment/landing_zone", "/obj/machinery/button/door/open_only/landing_zone")

FALLBACK = (
    ("/obj/item/shard/shrapnel", ("icons/obj/items/shards.dmi", "shrapnelmedium")),
    ("/obj/item/shard", ("icons/obj/items/shards.dmi", "medium")),
    ("/obj/machinery/iv_drip", ("icons/obj/iv_drip.dmi", "hooked")),
    ("/obj/effect/turf_decal/medical_decals/triage", ("icons/effects/medical_decals.dmi", "triagedecal")),
    ("/obj/structure/shuttle/engine/propulsion/burst/left", ("icons/turf/shuttle.dmi", "burst_l")),
    ("/obj/structure/shuttle/engine/propulsion/burst/right", ("icons/turf/shuttle.dmi", "burst_r")),
    ("/obj/structure/shuttle/engine/propulsion", ("icons/turf/shuttle.dmi", "propulsion")),
    ("/obj/structure/shuttle/engine/heater", ("icons/obj/factory/factory_machines.dmi", "heater")),
    ("/obj/item/clothing/mask/facehugger/dead", ("icons/Xeno/Effects.dmi", "facehugger_dead")),
    ("/obj/item/mmi", ("icons/obj/items/assemblies.dmi", "mmi_full")),
    ("/obj/item/evidencebag", ("icons/obj/items/storage/misc.dmi", "evidence")),
    ("/obj/item/assembly/igniter", ("icons/obj/assemblies/new_assemblies.dmi", "igniter")),
    ("/obj/item/instrument/guitar", ("icons/obj/musician.dmi", "guitar")),
    ("/obj/structure/musician/piano", ("icons/obj/musician.dmi", "piano")),
)

DIR_INDEX = {2: 0, 1: 1, 4: 2, 8: 3}  # BYOND SOUTH, NORTH, EAST, WEST -> the order tgmc_dmi.DIRS4 uses (S, N, E, W)


def _parse(path):
    cur = None
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        m = re.match(r"^(/[\w/]+)\s*(//.*)?$", line)
        if m:
            cur = m.group(1)
            DEFS.setdefault(cur, {})
            continue
        if cur and re.match(r"^\t(?:var/(?:[\w/]+/)?)?[a-z_]+\s*=", line):
            k, v = line.strip().split("=", 1)
            DEFS[cur][k.strip().split("/")[-1]] = re.sub(r"\s+//.*$", "", v).strip().rstrip(";")
        elif re.match(r"^\S", line):
            cur = None  # a proc (`/obj/thing/Initialize()`) or other code: its tabbed lines are not variables of the type


OBJECT_DIRS = ("code/game/objects", "code/game/turfs", "code/modules/flora", "code/modules/power", "code/modules/paperwork", "code/modules/reagents/chemistry/machinery",
               "code/modules/vehicles", "code/modules/recycling", "code/modules/atmospherics/machinery", "code/modules/hydroponics", "code/modules/mapping",
               "code/modules/food_and_drinks/kitchen_machinery", "code/modules/economy", "code/modules/shuttle", "code/modules/mining",
               "code/modules/clothing", "code/modules/reagents", "code/modules/food_and_drinks", "code/modules/projectiles", "code/modules/medical")


def load(tgmc, dirs=OBJECT_DIRS):
    if _loaded:
        return
    for d in dirs:
        for root, _, files in os.walk(os.path.join(tgmc, d)):
            for f in files:
                if f.endswith(".dm"):
                    _parse(os.path.join(root, f))
    _loaded.append(tgmc)


def resolve(path):
    out = {}
    parts = path.split("/")[1:]
    for i in range(1, len(parts) + 1):
        d = DEFS.get("/" + "/".join(parts[:i]))
        if d:
            out.update(d)
    return out


def _string(v):
    m = re.match(r"""^['"](.*)['"]$""", v or "")
    return m.group(1) if m else None


def _first_string(v):
    """A DM string, or the first of pick("a","b","c")."""
    if v is None:
        return None
    m = re.match(r"""^pick\(\s*['"]([^'"]*)['"]""", v)
    return m.group(1) if m else _string(v)


def _group(r):
    return r.get("smoothing_groups") or ""


def layers(path, vars_, states, near):
    """The pictures of one object: [(sheet, state, direction index)], bottom first; [] when it has none or is skipped.

    `near(dx, dy)` describes the cell at that offset for smoothing: it returns (objects, turf is solid), objects being (path, vars) pairs, or
    None outside the map."""
    if path.startswith(SKIP):
        return []
    r = resolve(path)
    icon = _first_string(vars_.get("icon")) or _first_string(r.get("icon"))
    state = _first_string(vars_.get("icon_state")) or _first_string(r.get("icon_state"))
    if not icon or not state:
        # TGMC sets these in code (an empty icon_state, or one chosen at runtime): a picture of the usual look.
        for prefix, pic in FALLBACK:
            if path.startswith(prefix):
                icon, state = pic
                break
    if not icon or not state:
        return []
    names = states(icon)
    if icon.endswith("decals_arrow.dmi") and state not in names:
        # The mapper's copy of the sign sheet has no safety signs, and the plain sheet has not either: they are on safety_signs.dmi.
        for other in ("decals", "safety_signs"):
            if state in states(icon.replace("decals_arrow", other)):
                icon = icon.replace("decals_arrow", other)
                break
        names = states(icon)
    if not names:
        return []
    direction = 0
    try:
        direction = DIR_INDEX.get(int(vars_.get("dir", "2")), 0)
    except ValueError:
        pass
    base = _first_string(vars_.get("base_icon_state")) or _first_string(r.get("base_icon_state"))
    if "SMOOTH_BITMASK" in r.get("smoothing_flags", "") and base:
        group = _group(r)
        closed = "CLOSED_TURFS" in r.get("canSmoothWith", "")

        def same(dx, dy):
            n = near(dx, dy)
            if n is None:
                return False
            objects, solid = n
            if closed and solid:
                return True
            return bool(group) and any(_group(resolve(p)) == group for p, _ in objects)

        n_, s_, e_, w_ = same(0, -1), same(0, 1), same(1, 0), same(-1, 0)
        m = (1 if n_ else 0) | (2 if s_ else 0) | (4 if e_ else 0) | (8 if w_ else 0)
        if n_ and e_ and same(1, -1):
            m |= 16
        if s_ and e_ and same(1, 1):
            m |= 32
        if s_ and w_ and same(-1, 1):
            m |= 64
        if n_ and w_ and same(-1, -1):
            m |= 128
        for candidate in (m, m & 15, 0):
            if f"{base}-{candidate}" in names:
                return [(icon, f"{base}-{candidate}", 0)]
    if state in names:
        return [(icon, state, direction)]
    return []


# Objects that can be shot to pieces: (path prefix, hit points, blocks movement while standing, stops bullets as cover). They become actors of the Neutral player
# (build_maptiles.py); everything else is baked into the floor tile.
DESTROYABLE = (
    ("/obj/structure/barricade", 300, True, True),
    ("/obj/structure/table", 150, True, False),
    ("/obj/structure/rack", 120, True, False),
    ("/obj/structure/closet", 100, True, True),
    ("/obj/structure/largecrate", 140, True, True),
    ("/obj/structure/fence", 90, True, False),
    ("/obj/structure/window", 80, True, True),
    ("/obj/structure/bed", 70, False, False),
    ("/obj/machinery/computer", 120, False, False),
    ("/obj/machinery/vending", 220, False, True),
    ("/obj/machinery/hydroponics", 90, False, False),
    ("/obj/structure/reagent_dispensers", 60, False, False),
)


def destroyable(path):
    """(hit points, blocks, cover) for an object that can be destroyed, or None."""
    if path.startswith("/obj/structure/window_frame"):
        return None  # an empty frame (a broken window): passable and no cover, only its picture
    for prefix, hp, blocks, cover in DESTROYABLE:
        if path.startswith(prefix):
            return hp, blocks, cover
    return None


def door_states(names, state):
    """For a door picture, its animation states: (closed, open, opening, closing, starts_open), or None when it is not a door TGMC animates this way.
    Airlocks and firedoors use door_closed / door_open / door_opening / door_closing; blast doors, shutters and the morgue door use pdoor1 / pdoor0 / pdoorc0 / pdoorc1
    (door1 / door0 / doorc0 / doorc1); windoors use left / leftopen / leftopening / leftclosing (and right, leftsecure, rightsecure)."""
    if state.endswith("_closed") or state.endswith("_open"):
        base = state.rsplit("_", 1)[0]
        found = (base + "_closed", base + "_open", base + "_opening", base + "_closing", state.endswith("_open"))
    elif re.match(r"^(left|right)(secure)?$", state):
        found = (state, state + "open", state + "opening", state + "closing", False)
    else:
        m = re.match(r"^(pdoor|shutter|door)([01]?)$", state)
        if not m:
            return None
        base = m.group(1)
        found = (base + "1" if base + "1" in names else base, base + "0", base + "c0", base + "c1", m.group(2) == "0")
    if found[0] not in names or found[1] not in names or found[2] not in names or found[3] not in names:
        return None
    return found


DOORS = ("/obj/machinery/door/airlock", "/obj/machinery/door/poddoor", "/obj/machinery/door/firedoor", "/obj/machinery/door/window", "/obj/machinery/door/morgue")


def is_door(path):
    """Doors that open for units on their own: airlocks, blast doors, shutters, firedoors, windoors and the morgue door."""
    return path.startswith(DOORS) 
