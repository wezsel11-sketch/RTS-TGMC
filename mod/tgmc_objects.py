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
        "/obj/structure/disposalpipe", "/obj/machinery/light", "/obj/item/", "/obj/effect/step_trigger", "/obj/effect/forcefield",
        "/mob/", "/obj/effect/alien", "/obj/structure/xeno", "/obj/effect/temp", "/obj/machinery/camera", "/obj/machinery/power/apc",
        "/obj/effect/abstract", "/obj/effect/turf_decal/warning_stripes/thin")

DIR_INDEX = {2: 0, 1: 1, 4: 2, 8: 3}  # BYOND SOUTH, NORTH, EAST, WEST -> the order tgmc_dmi.DIRS4 uses (S, N, E, W)


def _parse(path):
    cur = None
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        m = re.match(r"^(/[\w/]+)\s*$", line)
        if m:
            cur = m.group(1)
            DEFS.setdefault(cur, {})
            continue
        if cur and re.match(r"^\t[a-z_]+\s*=", line):
            k, v = line.strip().split("=", 1)
            DEFS[cur][k.strip()] = v.strip()
        elif re.match(r"^\S", line) and not line.startswith("/"):
            cur = None


def load(tgmc, dirs=("code/game/objects", "code/modules/flora", "code/game/turfs")):
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
        return []
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
