"""Read the turf of every cell from a TGMC .dmm map (TGM format, as written by dmm2tgm.py).

parse(path) returns (width, height, grid) where grid[x][y] is the turf path of the cell, y = 0 at the top (north)
edge. Only the first z level is read. Only the turf is kept: objects, areas and variable edits are ignored.
"""
import re

_KEY = re.compile(r'^"([A-Za-z]+)" = \($')
_BLOCK = re.compile(r"^\((\d+),(\d+),(\d+)\) = \{\"$")


def parse(path):
    turfs = {}  # key -> turf path
    columns = {}  # x -> list of keys, north to south
    key = None
    block = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if block is not None:
                if line == '"}':
                    block = None
                else:
                    block.append(line)
                continue
            m = _BLOCK.match(line)
            if m:
                block = []
                if m.group(3) == "1" and m.group(2) == "1":
                    columns[int(m.group(1))] = block
                else:
                    block = []  # another z level or a strip of the map we do not use: read and discard
                continue
            m = _KEY.match(line)
            if m:
                key = m.group(1)
                continue
            if key and line.startswith("/turf/"):
                turfs[key] = line.split("{")[0].rstrip(",)")
                key = None
    width = max(columns)
    height = len(columns[1])
    grid = [[turfs[k] for k in columns[x + 1]] for x in range(width)]
    return width, height, grid


def terrain(turf):
    """One of G(rass), D(irt or floor), F(ord, shallow water), W(deep water), R(ock, wall or void) for a turf path."""
    if turf.startswith(("/turf/closed/", "/turf/open/space", "/turf/open/chasm", "/turf/open/lava")):
        return "R"
    if turf.startswith("/turf/open/liquid/") or "/coast" in turf:
        return "W" if "deep" in turf else "F"
    if "impenetrable" in turf:
        return "R"
    if "grass" in turf or "jungle" in turf or "bushes" in turf:
        return "G"
    return "D"


def convert(grid, width, height, factor, box):
    """Crop grid to box (x0, y0, x1, y1, tiles) and shrink it by factor: rows of terrain letters, one per output row.

    A block is rock when more than half its tiles are, so thick rock stays solid while a one-tile wall or corridor survives
    only some of the time. Of the open tiles the commonest terrain wins, deep water counting for water only if it is the majority."""
    x0, y0, x1, y1 = box
    out = []
    for oy in range((y1 - y0) // factor):
        row = []
        for ox in range((x1 - x0) // factor):
            counts = {}
            for dx in range(factor):
                for dy in range(factor):
                    t = terrain(grid[x0 + ox * factor + dx][y0 + oy * factor + dy])
                    counts[t] = counts.get(t, 0) + 1
            if counts.get("R", 0) * 2 > factor * factor:
                row.append("R")
            else:
                counts.pop("R", None)
                row.append(max("WFGD", key=lambda t: counts.get(t, 0)))
        out.append("".join(row))
    return out


# The maps the mod converts. factor: how many TGMC tiles make one OpenRA cell. marines and xenos: where each base goes, in
# TGMC tiles (x, y from the top left corner of the .dmm), picked in open ground a good walk apart.
MAPS = {
    "lv-624": {"title": "LV-624", "file": "_maps/map_files/LV624/LV624.dmm", "factor": 2, "marines": (30, 128), "xenos": (150, 50)},
    "big-red": {"title": "Big Red", "file": "_maps/map_files/BigRed_v2/BigRed_v2.dmm", "factor": 3, "marines": (28, 118), "xenos": (130, 42)},
    "whiskey-outpost": {"title": "Whiskey Outpost", "file": "_maps/map_files/Whiskey_Outpost/Whiskey_Outpost_v2.dmm", "factor": 2, "marines": (60, 22), "xenos": (60, 112)},
    "desert-dam": {"title": "Desert Dam", "file": "_maps/map_files/desertdam/desertdam.dmm", "factor": 3, "marines": (40, 150), "xenos": (200, 150)},
}

# The same maps at TGMC's own size, one cell per tile (the ones above are shrunk to 1/2 or 1/3 so a match does not take an hour).
for _name, _spec in list(MAPS.items()):
    MAPS[_name + "-full"] = dict(_spec, title=_spec["title"] + " (full size)", factor=1)


def paths():
    return sorted(m["file"] for m in MAPS.values())


def crop_box(grid, width, height, f):
    """The crop load() uses: (x0, y0, x1, y1) in TGMC tiles, the open ground plus a margin, a whole number of f-tile blocks."""
    open_x = [x for x in range(width) if any(terrain(t) != "R" for t in grid[x])]
    open_y = [y for y in range(height) if any(terrain(grid[x][y]) != "R" for x in range(width))]
    x0, y0 = max(0, min(open_x) - 2 * f), max(0, min(open_y) - 2 * f)
    x1, y1 = min(width, max(open_x) + 1 + 2 * f), min(height, max(open_y) + 1 + 2 * f)
    return x0, y0, x0 + (x1 - x0) // f * f, y0 + (y1 - y0) // f * f


def load(tgmc, spec):
    """Convert one map: (rows, marines, xenos). rows is a list of terrain-letter strings, marines and xenos are the base
    centres in cells. The map is cropped to its open ground with a margin and shrunk by the spec's factor."""
    import os
    width, height, grid = parse(os.path.join(tgmc, spec["file"]))
    f = spec["factor"]
    x0, y0, x1, y1 = crop_box(grid, width, height, f)
    rows = convert(grid, width, height, f, (x0, y0, x1, y1))
    cell = lambda p: ((p[0] - x0) // f, (p[1] - y0) // f)  # noqa: E731
    return rows, cell(spec["marines"]), cell(spec["xenos"])


def parse_objects(path):
    """Every object on the first z level of a .dmm: (width, height, cells) where cells[x][y] is a list of (object path, {var: value}) for the
    /obj/ and /mob/ atoms of the cell, in the map's order (bottom first). Values are the raw DM text (`"name"` keeps its quotes)."""
    import re
    text = open(path, encoding="utf-8").read()
    defs = {}
    for m in re.finditer(r'^"([A-Za-z]+)" = \(\n(.*?)\)\n(?=")', text + '"', re.S | re.M):
        body = m.group(2)
        entries = []
        for e in re.finditer(r"(?m)^(/[\w/]+)(\{.*?\n\t\}|\{[^\n]*\})?,?", body, re.S):
            if not e.group(1).startswith(("/obj/", "/mob/")):
                continue
            vars_ = {}
            if e.group(2):
                for item in re.split(r";\n?|\n", e.group(2).strip("{}")):
                    item = item.strip()
                    if "=" in item:
                        k, v = item.split("=", 1)
                        vars_[k.strip()] = v.strip().rstrip(",")
            entries.append((e.group(1), vars_))
        defs[m.group(1)] = entries
    width, height, columns = 0, 0, {}
    block = None
    for line in text.split("\n"):
        if block is not None:
            if line == '"}':
                block = None
            else:
                block.append(line)
            continue
        m = _BLOCK.match(line)
        if m:
            block = []
            if m.group(3) == "1" and m.group(2) == "1":
                columns[int(m.group(1))] = block
            else:
                block = []
    width = max(columns)
    height = len(columns[1])
    return width, height, [[defs.get(k, []) for k in columns[x + 1]] for x in range(width)]
