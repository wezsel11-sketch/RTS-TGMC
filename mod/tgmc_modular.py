"""TGMC's modular map slots, filled in for the converted maps.

A TGMC map leaves some rooms as /obj/effect/spawner/modularmap markers. At round start the game loads one room template (a .dmm
under _maps/modularmaps) into each marker, picked at random from the templates with the marker's mapid. This module fills the
slots at build time instead, with the first template for each mapid in the order TGMC's code lists them. So each build is fixed.

Reads: code/modules/mapping/modular_mapping.dm (template list), code/game/objects/effects/spawners/modularmappingspawner.dm (marker
type -> mapid and size).
"""
import os
import random
import re

import tgmc_dmm


def templates(tgmc):
    """[(modular_id, path to the template .dmm)] in the order the code lists them, one entry per template."""
    text = open(os.path.join(tgmc, "code", "modules", "mapping", "modular_mapping.dm"), encoding="utf-8").read()
    out = []
    for block in re.split(r"\n(?=/datum/map_template/modular/)", text):
        m = re.match(r"/datum/map_template/modular/\S+\n", block)
        if not m:
            continue
        path = re.search(r'\n\tmappath = "([^"]+)"', block)
        mid = re.search(r'\n\tmodular_id = "([^"]+)"', block)
        if path and mid and path.group(1).endswith(".dmm"):
            out.append((mid.group(1), path.group(1)))
    return out


def marker_types(tgmc):
    """{marker type path: (mapid, width, height)} from the spawner definitions."""
    text = open(os.path.join(tgmc, "code", "game", "objects", "effects", "spawners", "modularmappingspawner.dm"), encoding="utf-8").read()
    out = {}
    for block in re.split(r"\n(?=/obj/effect/spawner/modularmap/)", text):
        m = re.match(r"(/obj/effect/spawner/modularmap/\S+)", block)
        if not m:
            continue
        mid = re.search(r'mapid = "([^"]+)"', block)
        w = re.search(r"spawner_width = (\d+)", block)
        h = re.search(r"spawner_height = (\d+)", block)
        if mid and w and h:
            out[m.group(1)] = (mid.group(1), int(w.group(1)), int(h.group(1)))
    return out


def apply(tgmc, width, height, grid, things):
    """Fill every marker in the map (grid, things as tgmc_dmm reads them) with its fixed template. Changes grid and things in place and
    returns the list of (x, y, template path) it placed, for the log."""
    kinds = marker_types(tgmc)
    first = {}
    for mid, path in templates(tgmc):
        first.setdefault(mid, path)
    placed = []
    for x in range(width):
        for y in range(height):
            markers = [(p, v) for p, v in things[x][y] if p in kinds]
            if not markers:
                continue
            mapid, sw, sh = kinds[markers[0][0]]
            path = first.get(mapid)
            if path is None:
                continue
            full = os.path.join(tgmc, path)
            if not os.path.exists(full):
                continue
            tw, th, tgrid = tgmc_dmm.parse(full)
            _, _, tthings = tgmc_dmm.parse_objects(full)
            if (tw, th) != (sw, sh):
                continue
            for dx in range(tw):
                for dy in range(th):
                    if x + dx < width and y + dy < height:
                        grid[x + dx][y + dy] = tgrid[dx][dy]
                        things[x + dx][y + dy] = [(p, v) for p, v in tthings[dx][dy]]
            placed.append((x, y, path))
    return placed


def fill_space(tgmc, width, height, grid, things):
    """Fill the empty space of a map with ground from its own modular rooms: every open floor type the templates use, spread over the
    cells by a fixed hash so each build looks the same. Objects stay where they are. Returns how many cells were filled."""
    counts = {}
    for _, path in templates(tgmc):
        full = os.path.join(tgmc, path)
        if not os.path.exists(full):
            continue
        tw, th, tgrid = tgmc_dmm.parse(full)
        for col in tgrid:
            for t in col:
                if t.startswith("/turf/open/") and not t.startswith("/turf/open/space"):
                    counts[t] = counts.get(t, 0) + 1
    # The most common floors of the rooms, in patches of six cells: a few kinds of ground, not a speckle of every tile.
    pool = sorted(sorted(counts, key=lambda t: -counts[t])[:6])
    if not pool:
        return 0
    filled = 0
    for x in range(width):
        for y in range(height):
            if grid[x][y].startswith("/turf/open/space"):
                grid[x][y] = pool[random.Random(f"{x // 6},{y // 6}").randrange(len(pool))]
                filled += 1
    return filled


def fill_void_with_rooms(tgmc, width, height, grid, things):
    """Tile the empty space with whole modular rooms: each room that fits entirely in void is placed where the scan reaches it, chosen by
    a fixed seed per position, so each build is the same. Rooms are written into grid and things. Returns how many were placed."""
    rooms = []
    for _, path in templates(tgmc):
        full = os.path.join(tgmc, path)
        if os.path.exists(full):
            tw, th, tgrid = tgmc_dmm.parse(full)
            _, _, tthings = tgmc_dmm.parse_objects(full)
            rooms.append((tw, th, tgrid, tthings))
    if not rooms:
        return 0
    placed = 0
    for y in range(height):
        for x in range(width):
            if not grid[x][y].startswith("/turf/open/space"):
                continue
            rng = random.Random(f"room {x},{y}")
            order = list(range(len(rooms)))
            rng.shuffle(order)
            for i in order:
                tw, th, tgrid, tthings = rooms[i]
                if x + tw > width or y + th > height:
                    continue
                if any(not grid[x + dx][y + dy].startswith("/turf/open/space") for dx in range(tw) for dy in range(th)):
                    continue
                for dx in range(tw):
                    for dy in range(th):
                        grid[x + dx][y + dy] = tgrid[dx][dy]
                        things[x + dx][y + dy] = [(p, v) for p, v in tthings[dx][dy]]
                placed += 1
                break
    return placed
