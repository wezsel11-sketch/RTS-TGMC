"""Which TGMC floor or wall picture each cell of a TGMC .dmm map shows, so the converted maps look like the real ones.

TGMC defines every turf in DM code (code/game/turfs): an `icon` sheet and an `icon_state`, inherited down the path (/turf/open/floor/tile/dark
is a /turf/open/floor/tile is a /turf/open/floor ...). resolve(path) reads that. Walls and a few floors are "smoothed": the picture depends on
which neighbours are of the same kind, chosen by an 8-bit mask of the neighbours (north 1, south 2, east 4, west 8 and, only when both of their
sides are set, north-east 16, south-east 32, south-west 64, north-west 128), and the sheet holds the 47 states `<name>-<mask>` that can occur.

cell_tile(grid, x, y) returns (sheet path, state name) for one cell; None means "draw nothing special" (the caller picks a plain ground tile).
"""
import os
import re

DEFS = {}
_loaded = []


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
        if cur and re.match(r"^\t[a-z_]+\s*=", line):
            k, v = line.strip().split("=", 1)
            DEFS[cur][k.strip()] = v.strip()
        elif re.match(r"^\S", line) and not line.startswith("/"):
            cur = None


def load(tgmc):
    if _loaded:
        return
    for root, _, files in os.walk(os.path.join(tgmc, "code", "game", "turfs")):
        for f in files:
            if f.endswith(".dm"):
                _parse(os.path.join(root, f))
    _loaded.append(tgmc)


def resolve(path):
    """The variables a turf path ends up with, nearest definition winning."""
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


def solid(turf):
    return turf.startswith("/turf/closed/")


def mask(grid, x, y, same):
    """The smoothing mask of cell (x, y): which of its neighbours `same(turf)` calls like it. Out of the map counts as the same, as TGMC's borders do."""
    w, h = len(grid), len(grid[0])

    def near(dx, dy):
        nx, ny = x + dx, y + dy
        return True if not (0 <= nx < w and 0 <= ny < h) else same(grid[nx][ny])

    n, s, e, wst = near(0, -1), near(0, 1), near(1, 0), near(-1, 0)
    m = (1 if n else 0) | (2 if s else 0) | (4 if e else 0) | (8 if wst else 0)
    if n and e and near(1, -1):
        m |= 16
    if s and e and near(1, 1):
        m |= 32
    if s and wst and near(-1, 1):
        m |= 64
    if n and wst and near(-1, -1):
        m |= 128
    return m


def cell_tile(grid, x, y, states):
    """(sheet, state) for one cell. `states(sheet)` returns the set of state names a sheet has."""
    turf = grid[x][y]
    r = resolve(turf)
    icon, state = _string(r.get("icon")), _string(r.get("icon_state"))
    if not icon or not state:
        return None
    if "SMOOTH_BITMASK" in r.get("smoothing_flags", ""):
        base = _string(r.get("base_icon_state")) or re.sub(r"-\d+$|-icon$", "", state)
        if solid(turf):
            same = solid
        else:
            same = lambda t: t == turf  # noqa: E731
        m = mask(grid, x, y, same)
        names = states(icon)
        for candidate in (m, m & 15, 0):
            if f"{base}-{candidate}" in names:
                return icon, f"{base}-{candidate}"
        return icon, state
    return icon, state
