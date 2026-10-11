"""Build the LV-624 skirmish map from TGMC's own map file.

TGMC's `LV624.dmm` is a BYOND map, 220 x 180 cells. This reads it, crops the part between the marine landing zone and the
xeno caves, turns each turf into one of the mod's terrain tiles, and writes an OpenRA map folder (`maps/lv624`) with the
marines at the landing zone and the xenos at the spot where TGMC spawns them in the caves.

  - Marines start at the centre of `LZ_AREA` (the second landing zone, in the west of the colony).
  - Xenos start in the open cave nearest TGMC's `xeno_spawner_spawn` landmark (a cramped walled room): the cave cell with
    the most open ground around it, within CAVE_AREA, so there is room to build a hive.
  - The crop is the box round both, padded (CROP_PAD), so the real layout is kept at one cell per turf.

Like the art, the result goes to the git-ignored build folder and is for personal use only: it is TGMC's map.

How a turf is read (see `classify`): walls and windows block, dense jungle and trees block (Brush), mineral rock blocks (Rock),
river is a ford, deep river is water, a catwalk makes walkable ground of whatever is under it, grass is Clear, dirt is a
road above ground and cave floor below it, and every other floor is a colony floor. Objects are ignored except windows,
trees and catwalks. If the water or walls cut the two bases apart, a path is carved between them (and reported), so the
map can always be played.

Usage: build_map.py --tgmc CHECKOUT [--out DIR]
"""
import argparse
import collections
import os
import random
import re
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DMM = "_maps/map_files/LV624/LV624.dmm"
LZ_AREA = "/area/shuttle/drop2/lz2"
XENO_LANDMARK = "/obj/effect/landmark/xeno_spawner_spawn"
CAVE_AREA = "/area/lv624/ground/caves/central5"  # the cave the xenos start in; the crop takes in all of it
CROP_PAD = 10
MAX_SIZE = 140

# Terrain kinds -> the tileset template ids to pick from (each a 1x1 template with one picture; see tilesets/ground.yaml).
GRASS, WATER, FORD, DIRT, ROCK, WALL, BRUSH, FLOOR, CAVE = "grass", "water", "ford", "dirt", "rock", "wall", "brush", "floor", "cave"
PLATING = "plating"
TEMPLATE = {GRASS: (1, 12), WATER: (2,), FORD: (3,), DIRT: (4,), ROCK: (5, 10), WALL: (6,), BRUSH: (7,),
            FLOOR: (8,), PLATING: (11,), CAVE: (9,)}
WALKABLE = {GRASS, DIRT, CAVE, FLOOR, PLATING}  # where a structure may stand
PASSABLE = WALKABLE | {FORD}                    # where a unit may walk
# The radar and preview colours, matching tilesets/ground.yaml
COLOUR = {GRASS: (0x2E, 0x52, 0x30), WATER: (0x4D, 0x86, 0xB8), FORD: (0x92, 0xA6, 0xA1), DIRT: (0x5C, 0x4C, 0x37),
          ROCK: (0x3E, 0x35, 0x2D), WALL: (0x8A, 0x92, 0x98), BRUSH: (0x22, 0x38, 0x1F), FLOOR: (0x9A, 0x96, 0x80),
          PLATING: (0x50, 0x50, 0x54), CAVE: (0x4A, 0x40, 0x38)}


# ---------------------------------------------------------------- reading the .dmm

def _split_top_level(text):
    """Split `a, b{x = 1, y = 2}, c` on the commas that are not inside braces."""
    parts, depth, cur = [], 0, []
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur).strip())
    return parts


def read_dmm(path):
    """Return (width, height, grid), where grid[y][x] = (turf, area, [object types]) and row 0 is the north edge.

    TGMC saves maps in the "tgm" layout: a dictionary of 3-letter keys, then one block per column x, whose rows run from
    the north edge to the south edge."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    cells = {}
    for m in re.finditer(r'^"([A-Za-z]+)" = \(\n(.*?)\)\n\n?(?=^"|^\(\d)', text, re.S | re.M):
        parts = [p.split("{")[0].strip() for p in _split_top_level(m.group(2))]
        cells[m.group(1)] = (parts[-2], parts[-1], parts[:-2])
    columns = {}
    for m in re.finditer(r'^\((\d+),(\d+),(\d+)\) = \{"\n(.*?)\n"\}', text, re.S | re.M):
        columns[int(m.group(1))] = m.group(4).split("\n")
    if not cells or not columns:
        raise SystemExit(f"{path}: no map data found; is this a tgm-format .dmm?")
    width, height = max(columns), len(columns[1])
    try:
        grid = [[cells[columns[x][y]] for x in range(1, width + 1)] for y in range(height)]
    except KeyError as e:
        raise SystemExit(f"{path}: the grid names a key {e} that the dictionary does not define")
    return width, height, grid


# ---------------------------------------------------------------- turf -> terrain

def classify(turf, area, objs):
    """The terrain kind for one cell."""
    def has(prefix):
        return any(o.startswith(prefix) for o in objs)

    if turf.startswith("/turf/closed/wall"):
        return WALL
    if turf.startswith("/turf/closed/gm"):
        return BRUSH
    if turf.startswith("/turf/closed/") or turf.startswith("/turf/open/space"):
        return ROCK
    if turf.startswith("/turf/open/liquid/water"):
        if has("/obj/structure/catwalk"):
            return PLATING
        return WATER if "deep" in turf else FORD
    if has("/obj/structure/window") or has("/obj/structure/window_frame"):
        return WALL
    if has("/obj/structure/flora/tree"):
        return BRUSH
    if turf.startswith("/turf/open/ground/grass") or turf.startswith("/turf/open/floor/grass"):
        return GRASS
    if turf.startswith("/turf/open/ground/coast") or turf.startswith("/turf/open/ground/beach"):
        return DIRT
    if turf.startswith("/turf/open/floor/plating/ground/dirtgrassborder"):
        return GRASS
    if turf.startswith("/turf/open/floor/plating/ground/dirt"):
        return CAVE if "/caves/" in area else DIRT
    if turf.startswith("/turf/open/floor/plating") or turf.startswith("/turf/open/floor/tile/dark") \
            or turf.startswith("/turf/open/floor/engine"):
        return PLATING
    if turf.startswith("/turf/open/floor"):
        return FLOOR
    return None


# ---------------------------------------------------------------- the map

class Layout:
    """The cropped grid of terrain kinds, and the cells already taken by structures and units."""

    def __init__(self, kinds):
        self.kinds = kinds
        self.h, self.w = len(kinds), len(kinds[0])
        self.taken = set()

    def passable(self, x, y):
        return 0 < x < self.w - 1 and 0 < y < self.h - 1 and self.kinds[y][x] in PASSABLE

    def free(self, x, y):
        return (x, y) not in self.taken and 1 < x < self.w - 2 and 1 < y < self.h - 2 and self.kinds[y][x] in WALKABLE

    def find_rect(self, near, width, height, below=0, margin=0):
        """The nearest top-left cell, spiralling out from `near`, where a width x height block fits on walkable ground.
        `below` more rows beneath it must be passable and untaken too (the exit cells of a producer), and `margin`
        cells around it must be untaken (so structures do not touch)."""
        nx, ny = near
        for radius in range(0, 40):
            ring = [(nx + dx, ny + dy) for dx in range(-radius, radius + 1) for dy in range(-radius, radius + 1)
                    if max(abs(dx), abs(dy)) == radius]
            ring.sort(key=lambda p: (p[0] - nx) ** 2 + (p[1] - ny) ** 2)
            for x, y in ring:
                if all(self.free(cx, cy) for cx in range(x, x + width) for cy in range(y, y + height)) \
                        and all(self.passable(cx, cy) and (cx, cy) not in self.taken
                                for cx in range(x, x + width) for cy in range(y + height, y + height + below)) \
                        and all((cx, cy) not in self.taken
                                for cx in range(x - margin, x + width + margin) for cy in range(y - margin, y + height + margin)):
                    return x, y
        raise SystemExit(f"no room for a {width}x{height} block near {near}")

    def take(self, x, y, width, height, below=0):
        for cx in range(x, x + width):
            for cy in range(y, y + height + below):
                self.taken.add((cx, cy))

    def find_cell(self, near):
        x, y = self.find_rect(near, 1, 1)
        self.taken.add((x, y))
        return x, y

    def clearance(self):
        """For each cell, how many steps it is from the nearest cell that cannot be built on (a multi-source BFS)."""
        dist = {}
        todo = collections.deque()
        for y in range(self.h):
            for x in range(self.w):
                if self.kinds[y][x] not in WALKABLE:
                    dist[(x, y)] = 0
                    todo.append((x, y))
        while todo:
            x, y = todo.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < self.w and 0 <= n[1] < self.h and n not in dist:
                    dist[n] = dist[(x, y)] + 1
                    todo.append(n)
        return dist

    def path_exists(self, a, b):
        seen, todo = {a}, collections.deque([a])
        while todo:
            x, y = todo.popleft()
            if (x, y) == b:
                return True
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                n = (x + dx, y + dy)
                if n not in seen and self.passable(*n):
                    seen.add(n)
                    todo.append(n)
        return False

    def carve(self, a, b):
        """Open the cheapest route from a to b (Dijkstra; blocked cells cost more than open ones) and return how many
        cells had to be opened. Opened cells become dirt, or a ford over water."""
        cost = {a: 0}
        came = {}
        todo = [(0, a)]
        import heapq
        while todo:
            c, p = heapq.heappop(todo)
            if p == b:
                break
            if c > cost[p]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (p[0] + dx, p[1] + dy)
                if not (0 < n[0] < self.w - 1 and 0 < n[1] < self.h - 1):
                    continue
                step = 1 if self.kinds[n[1]][n[0]] in PASSABLE else 12
                if c + step < cost.get(n, 1 << 30):
                    cost[n] = c + step
                    came[n] = p
                    heapq.heappush(todo, (c + step, n))
        opened, p = 0, b
        while p != a:
            x, y = p
            if self.kinds[y][x] not in PASSABLE:
                self.kinds[y][x] = FORD if self.kinds[y][x] == WATER else DIRT
                opened += 1
            p = came[p]
        return opened


def crop_box(width, height, grid):
    """Find the landing zone and the xeno spawn, and return (x0, y0, x1, y1, marine_xy, xeno_xy) in map cells."""
    lz = [(x, y) for y in range(height) for x in range(width) if grid[y][x][1] == LZ_AREA]
    xeno = [(x, y) for y in range(height) for x in range(width) if XENO_LANDMARK in grid[y][x][2]]
    cave = [(x, y) for y in range(height) for x in range(width) if grid[y][x][1].startswith(CAVE_AREA)]
    if not lz or not xeno or not cave:
        raise SystemExit(f"LV624.dmm has no {LZ_AREA}, {XENO_LANDMARK} or {CAVE_AREA}: the map has changed, update build_map.py")
    pts = lz + cave + xeno
    x0, x1 = min(p[0] for p in pts) - CROP_PAD, max(p[0] for p in pts) + CROP_PAD
    y0, y1 = min(p[1] for p in pts) - CROP_PAD, max(p[1] for p in pts) + CROP_PAD
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(width - 1, x1), min(height - 1, y1)
    if max(x1 - x0, y1 - y0) + 1 > MAX_SIZE:
        raise SystemExit(f"the crop {x1 - x0 + 1}x{y1 - y0 + 1} is over {MAX_SIZE}: lower CROP_PAD")
    marine = (sum(p[0] for p in lz) // len(lz), sum(p[1] for p in lz) // len(lz))
    return x0, y0, x1, y1, marine, xeno[0]


def build(tgmc, out):
    import make_placeholders as mp  # the map writer is shared with the other maps

    width, height, grid = read_dmm(os.path.join(tgmc, DMM))
    x0, y0, x1, y1, marine_at, xeno_at = crop_box(width, height, grid)
    unknown = collections.Counter()
    kinds = []
    for y in range(y0, y1 + 1):
        row = []
        for x in range(x0, x1 + 1):
            kind = classify(*grid[y][x])
            if kind is None:
                unknown[grid[y][x][0]] += 1
                kind = DIRT
            row.append(kind)
        kinds.append(row)
    for turf, n in unknown.most_common(8):
        print(f"lv624: unknown turf {turf} ({n} cells) read as dirt")
    # The edge is a wall of rock: the playable area is inside it (Bounds in map.yaml)
    for x in range(len(kinds[0])):
        kinds[0][x] = kinds[-1][x] = ROCK
    for row in kinds:
        row[0] = row[-1] = ROCK

    lay = Layout(kinds)
    marine_at = (marine_at[0] - x0, marine_at[1] - y0)
    xeno_at = (xeno_at[0] - x0, xeno_at[1] - y0)
    # The landmark is in a small walled room. Start the hive in the roomiest part of the cave instead (the cave cell with the
    # most open ground around it, nearest the landmark among equals).
    roomy = lay.clearance()
    cave_cells = [(x - x0, y - y0) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
                  if grid[y][x][1].startswith(CAVE_AREA) and kinds[y - y0][x - x0] in WALKABLE]
    best = max(cave_cells, key=lambda p: (min(roomy.get(p, 0), 9), -((p[0] - xeno_at[0]) ** 2 + (p[1] - xeno_at[1]) ** 2)))
    print(f"lv624: xeno hive moved from the spawner room {xeno_at} to the open cave at {best} ({roomy[best]} cells of room)")
    xeno_at = best

    # The two bases. A producer keeps its exit cells (below it) clear; structures keep a cell between them.
    placed = []

    def put(name, owner, near, size=(1, 1), below=0, facing=0, margin=0):
        x, y = lay.find_rect(near, size[0], size[1], below, margin)
        lay.take(x, y, size[0], size[1], below)
        placed.append((name, owner, x, y, facing))
        return x, y

    mx, my = put("cryo-pod", "Marines", marine_at, (1, 2), below=2, facing=512)
    spawn_marine = (mx, my)
    put("vendor", "Marines", (mx + 4, my), (1, 1), below=2, facing=512)
    put("sentry-turret", "Marines", (mx - 5, my - 6), facing=256)
    put("sentry-turret", "Marines", (mx + 6, my - 6), facing=256)
    for unit, dx in (("rifleman", -2), ("rifleman", -1), ("rifleman", 0), ("rifleman", 1), ("medic", 2), ("engineer", 3)):
        x, y = lay.find_cell((mx + dx, my + 6))
        placed.append((unit, "Marines", x, y, 256))

    sx, sy = put("resin-silo", "Xenos", xeno_at, (3, 3), below=3, facing=768, margin=1)
    spawn_xeno = (sx + 1, sy + 1)
    put("mini-silo", "Xenos", (sx - 6, sy + 1), (2, 2), below=2, facing=768, margin=1)
    put("mini-silo", "Xenos", (sx + 7, sy + 1), (2, 2), below=2, facing=768, margin=1)
    put("resin-turret", "Xenos", (sx - 3, sy + 8), facing=768, margin=1)
    put("resin-turret", "Xenos", (sx + 5, sy + 8), facing=768, margin=1)
    for i, unit in enumerate(("runner", "runner", "runner", "runner", "hunter", "sentinel", "drone", "queen")):
        x, y = lay.find_cell((sx + 1 + (i % 4) - 2, sy + 9 + i // 4))
        placed.append((unit, "Xenos", x, y, 768))

    # Make sure the marines can walk to the xenos. If water or walls cut them apart, open the cheapest route.
    a, b = (spawn_marine[0], spawn_marine[1] + 3), (spawn_xeno[0], spawn_xeno[1] + 4)
    carved = 0
    if not lay.path_exists(a, b):
        carved = lay.carve(a, b)
        print(f"lv624: no walkable route from the landing zone to the caves; opened {carved} cells")

    # Print how the two sides are linked, for the log
    kind_count = collections.Counter(k for row in lay.kinds for k in row)
    print("lv624: %dx%d cells cropped from (%d,%d); marines at %s, xenos at %s; %s" % (
        lay.w, lay.h, x0, y0, spawn_marine, spawn_xeno,
        ", ".join(f"{k} {n}" for k, n in sorted(kind_count.items(), key=lambda kv: -kv[1]))))

    rnd = random.Random(624)
    picks = {}
    for y in range(lay.h):
        for x in range(lay.w):
            picks[(x, y)] = (rnd.choice(TEMPLATE[lay.kinds[y][x]]), 0)

    def ground(x, y):
        return picks[(x, y)]

    preview = Image.new("RGBA", (lay.w, lay.h))
    for y in range(lay.h):
        for x in range(lay.w):
            preview.putpixel((x, y), COLOUR[lay.kinds[y][x]] + (255,))

    mp.write_map(os.path.join(out, "maps", "lv624"), "LV-624", lay.w, lay.h, placed, "Lobby",
                 [spawn_marine, spawn_xeno], ground=ground, category="Conquest", preview=preview)
    # The same ground with a bot on each side, for mod/balance.sh (`balance.sh 4 600 balance-lv624`)
    mp.write_map(os.path.join(out, "maps", "balance-lv624"), "balance-lv624", lay.w, lay.h, placed, "MissionSelector",
                 [spawn_marine, spawn_xeno], scripts=("test-aivai",), ground=ground, xeno_bot="skirmish",
                 marine_bot="skirmish", fast=True, preview=preview)
    return carved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", required=True, help="path to a terragov-marine-corps checkout")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "mod", "tgmc"))
    args = ap.parse_args()
    build(args.tgmc, args.out)


if __name__ == "__main__":
    main()
