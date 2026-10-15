"""Cut the real TGMC floor and wall pictures a converted map uses into OpenRA terrain tiles, and add them to the tileset.

For each full-size map (tgmc_dmm.MAPS entries with factor 1) every cell is looked up with tgmc_turfs.cell_tile and the 32x32 picture is cut out of
its .dmi sheet. The pictures become one-tile terrain templates in the tileset (ids from FIRST_ID), with the terrain type the cell had before
(floor = Clear, wall and rock and void = Rock, water = Water or Ford), so the maps play as before and look like TGMC. Void (space) is black.

Objects on the map (tables, barricades, plants, doors, decals; see tgmc_objects.py) are baked into the tile under them, so a tile is a floor
picture plus the pictures of the objects standing on it. They do not block movement.

prepare(tgmc, out) writes out/tiles/<id>.png and out/tilesets/ground.yaml (the repo's own tileset plus the new templates) and returns a Tiles object
whose art(name) gives, for a map, a function (x, y) -> template id for the cell in the cropped map.
"""
import os
import sys

from PIL import Image, PngImagePlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgmc_dmi  # noqa: E402
import tgmc_dmm  # noqa: E402
import tgmc_objects  # noqa: E402
import tgmc_turfs  # noqa: E402

FIRST_ID = 100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TERRAIN = {"G": "Clear", "D": "Clear", "F": "Ford", "W": "Water", "R": "Rock"}


COLOURS = {}  # template id -> the picture's average colour, for the map preview


class Tiles:
    def __init__(self):
        self.ids = {}       # (sheet, state) or "void" -> template id
        self.terrain = {}   # key -> terrain type
        self.maps = {}      # map name -> (x0, y0, width, height, grid, keys)

    def id_for(self, key, terrain):
        if key not in self.ids:
            self.ids[key] = FIRST_ID + len(self.ids)
            self.terrain[key] = terrain
        return self.ids[key]

    def art(self, name):
        x0, y0, w, h, grid = self.maps[name]

        def at(x, y):
            return self.cell_ids[name][y][x]
        return at


def prepare(tgmc, out, names):
    tgmc_turfs.load(tgmc)
    tgmc_objects.load(tgmc)
    sheets = {}

    def states(icon):
        if icon not in sheets:
            path = os.path.join(tgmc, icon)
            sheets[icon] = tgmc_dmi.Dmi(path) if os.path.exists(path) else None
        return {s["name"] for s in sheets[icon].states} if sheets[icon] else set()

    tiles = Tiles()
    tiles.cell_ids = {}
    for name in names:
        spec = tgmc_dmm.MAPS[name]
        width, height, grid = tgmc_dmm.parse(os.path.join(tgmc, spec["file"]))
        _, _, things = tgmc_dmm.parse_objects(os.path.join(tgmc, spec["file"]))
        x0, y0, x1, y1 = tgmc_dmm.crop_box(grid, width, height, spec["factor"])

        def near_at(x, y):
            def near(dx, dy):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    return None
                return things[nx][ny], grid[nx][ny].startswith("/turf/closed/")
            return near

        rows = []
        for y in range(y0, y1):
            row = []
            for x in range(x0, x1):
                turf = grid[x][y]
                kind = tgmc_dmm.terrain(turf)
                if turf.startswith("/turf/open/space"):
                    key = "void"
                else:
                    key = tgmc_turfs.cell_tile(grid, x, y, states)
                    if key is None or key[1] not in states(key[0]):
                        key = "plain-" + kind
                on = []
                if key != "void":
                    for path, vars_ in things[x][y]:
                        for layer in tgmc_objects.layers(path, vars_, states, near_at(x, y)):
                            dmi = sheets.get(layer[0])
                            if dmi is not None and dmi.icon_w <= 32:
                                on.append(layer)
                row.append(tiles.id_for((key, tuple(on)) if on else key, TERRAIN[kind]))
            rows.append(row)
        tiles.cell_ids[name] = rows
        tiles.maps[name] = (x0, y0, x1 - x0, y1 - y0, grid)

    # The pictures
    os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
    average = {}
    for key, tid in tiles.ids.items():
        objects = ()
        if isinstance(key, tuple) and len(key) == 2 and isinstance(key[1], tuple):
            key, objects = key
        if key == "void":
            img = Image.new("RGBA", (32, 32), (0, 0, 0, 255))
        elif isinstance(key, str):  # plain ground when a turf has no picture of its own
            img = Image.new("RGBA", (32, 32), {"plain-G": (46, 82, 48, 255), "plain-D": (92, 76, 55, 255), "plain-F": (146, 166, 161, 255),
                                                "plain-W": (77, 134, 184, 255), "plain-R": (60, 60, 60, 255)}[key])
        else:
            frame = sheets[key[0]].frames(key[1])[0][0].convert("RGBA")
            img = Image.new("RGBA", (32, 32), (0, 0, 0, 255))
            img.alpha_composite(frame.crop((0, 0, 32, 32)))
        for sheet, state, direction in objects:
            frames = sheets[sheet].frames(state)[0]
            part = frames[direction if direction < len(frames) else 0].convert("RGBA")
            img.alpha_composite(part.crop((0, part.height - 32, part.width, part.height)).crop((0, 0, 32, 32)))
        px = list(img.convert("RGB").getdata())
        COLOURS[tid] = tuple(sum(c[i] for c in px) // len(px) for i in range(3)) + (255,)
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", "32,32")
        meta.add_text("FrameAmount", "1")
        img.save(os.path.join(out, "tiles", f"m{tid}.png"), pnginfo=meta)

    # The tileset: the repo's own templates and one per picture
    base = open(os.path.join(ROOT, "tgmc", "tilesets", "ground.yaml"), encoding="utf-8").read().rstrip("\n") + "\n"
    # All templates share one sheet, so it has to be big enough for the repo's own tiles and every picture (32x32 each).
    side = 512
    while (side // 32) ** 2 < (len(tiles.ids) + 16) * 1.15:
        side *= 2
    base = base.replace("SheetSize: 512", f"SheetSize: {side}", 1)
    lines = []
    for key, tid in tiles.ids.items():
        category = {"Rock": "Terrain", "Clear": "Terrain", "Ford": "Water", "Water": "Water"}[tiles.terrain[key]]
        lines += [f"\tTemplate@{tid}:", f"\t\tId: {tid}", f"\t\tImages: tiles/m{tid}.png", "\t\tSize: 1,1", "\t\tPickAny: True",
                  f"\t\tCategories: {category}", "\t\tTiles:", f"\t\t\t0: {tiles.terrain[key]}"]
    os.makedirs(os.path.join(out, "tilesets"), exist_ok=True)
    with open(os.path.join(out, "tilesets", "ground.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(base + "\n".join(lines) + "\n")
    return tiles
