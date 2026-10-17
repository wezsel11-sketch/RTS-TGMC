# mod/alamo_footprint.py
"""Cells of TGMC's Alamo dropship map, read from its piece layout (see the design spec).

The .dmm has one block per column (x = 1..11, y = 1, z = 1). Each block is a list of keys, one per row, top to bottom.
Each key is defined once as `"key" = ( ... )` with the atoms of that cell.
"""
import re

_DEF = re.compile(r'^"([a-zA-Z]+)" = \(\n(.*?)\)\n(?=")', re.S | re.M)
_BLOCK = re.compile(r'^\((\d+),1,1\) = \{"\n(.*?)\n"\}', re.S | re.M)


def _read(path):
    text = open(path, encoding="utf-8").read()
    defs = {key: body for key, body in _DEF.findall(text + '"')}
    columns = {int(x): body.split("\n") for x, body in _BLOCK.findall(text)}
    return defs, columns


def _is_piece(body):
    return "dropship_piece" in body or "dropship_hatch" in body


def footprint(path):
    """Cells (x, row) of the Alamo, origin at the top-left cell of the footprint."""
    defs, columns = _read(path)
    cells = [(x, row) for x, keys in columns.items() for row, key in enumerate(keys)
             if _is_piece(defs.get(key, ""))]
    ox = min(x for x, _ in cells)
    oy = min(row for _, row in cells)
    return [(x - ox, row - oy) for x, row in cells]


def hatch(path):
    """The first dropship hatch cell, relative to the same origin as footprint()."""
    defs, columns = _read(path)
    cells = [(x, row) for x, keys in columns.items() for row, key in enumerate(keys)
             if "dropship_hatch" in defs.get(key, "")]
    ox = min(x for x, _ in footprint_raw(path))
    oy = min(row for _, row in footprint_raw(path))
    x, row = min(cells)
    return (x - ox, row - oy)


def footprint_raw(path):
    defs, columns = _read(path)
    return [(x, row) for x, keys in columns.items() for row, key in enumerate(keys) if _is_piece(defs.get(key, ""))]
