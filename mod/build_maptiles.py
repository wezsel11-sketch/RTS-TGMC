"""Cut the real TGMC floor and wall pictures a converted map uses into OpenRA terrain tiles, and add them to the tileset.

For each full-size map (tgmc_dmm.MAPS entries with factor 1) every cell is looked up with tgmc_turfs.cell_tile and the 32x32 picture is cut out of
its .dmi sheet. The pictures become one-tile terrain templates in the tileset (ids from FIRST_ID), with the terrain type the cell had before
(floor = Clear, a wall = Wall or ReinforcedWall, which heavy weapons can knock down, rock and void = Rock, water = Water or Ford), so the maps play as before and look like TGMC. Void (space) is black.

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


def terrain_of(turf, kind):
    """The terrain type of a cell: its letter's, except that a plain wall is Wall and a reinforced one ReinforcedWall (they can be shot down)."""
    if turf.startswith("/turf/closed/wall/r_wall") and "unmeltable" not in turf and "indestructible" not in turf:
        return "ReinforcedWall"
    if turf.startswith("/turf/closed/wall") and not turf.startswith("/turf/closed/wall/r_wall") and "indestructible" not in turf:
        return "Wall"
    return TERRAIN[kind]



COLOURS = {}  # template id -> the picture's average colour, for the map preview


class Tiles:
    def __init__(self):
        self.pictures = {}   # (sheet, state, direction) -> index in sprites/mapobjects.png
        self.types = {}      # (picture, hit points, blocks) -> actor name mapobj-<n>
        self.actors = {}     # map name -> [(actor type, x, y)] in the cropped map

        self.ids = {}       # (sheet, state) or "void" -> template id
        self.terrain = {}   # key -> terrain type
        self.maps = {}      # map name -> (x0, y0, width, height, grid, keys)

    def object_type(self, picture, hp, blocks, cover=False):
        key = (picture, hp, blocks, cover and blocks)
        if key not in self.types:
            self.types[key] = f"mapobj-{len(self.types)}"
        return self.types[key]

    def open_variant(self, name):
        """The same object without the movement blocking (used when a blocker would cut a base off or sit on a base)."""
        for (picture, hp, blocks, cover), n in list(self.types.items()):
            if n == name:
                return self.object_type(picture, hp, False)
        return name

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
                    solid_here = False
                    for path, vars_ in things[x][y]:
                        dest = tgmc_objects.destroyable(path)
                        for layer in tgmc_objects.layers(path, vars_, states, near_at(x, y)):
                            dmi = sheets.get(layer[0])
                            if dmi is None or dmi.icon_w > 32:
                                continue
                            if dest:
                                hp, blocks, cover = dest
                                # Rock under it (a window in a wall) is blocked anyway; two blockers on one cell are one too many.
                                blocks = blocks and kind in "GDF" and not solid_here
                                solid_here = solid_here or blocks
                                pic = tiles.pictures.setdefault(layer, len(tiles.pictures))
                                tiles.actors.setdefault(name, []).append((tiles.object_type(pic, hp, blocks, cover), x - x0, y - y0))
                            else:
                                on.append(layer)
                row.append(tiles.id_for((key, tuple(on)) if on else key, terrain_of(turf, kind)))
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

    for (picture, hp, blocks, cover) in list(tiles.types):  # every blocking object also has an open twin, for when it must not block
        if blocks:
            tiles.object_type(picture, hp, False)
    # The destroyable objects: their pictures on one sheet, a sequence for each, and an actor type for each combination
    os.makedirs(os.path.join(out, "sprites"), exist_ok=True)
    count = max(1, len(tiles.pictures))
    sheet = Image.new("RGBA", (32 * count, 32), (0, 0, 0, 0))
    for (sheet_path, state, direction), index in tiles.pictures.items():
        frames = sheets[sheet_path].frames(state)[0]
        part = frames[direction if direction < len(frames) else 0].convert("RGBA")
        sheet.alpha_composite(part.crop((0, part.height - 32, part.width, part.height)).crop((0, 0, 32, 32)), (32 * index, 0))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("FrameSize", "32,32")
    meta.add_text("FrameAmount", str(count))
    sheet.save(os.path.join(out, "sprites", "mapobjects.png"), pnginfo=meta)
    os.makedirs(os.path.join(out, "sequences"), exist_ok=True)
    with open(os.path.join(out, "sequences", "mapobjects.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# Generated by mod/build_maptiles.py. Do not edit.\nmapobj:\n\tDefaults:\n\t\tFilename: sprites/mapobjects.png\n")
        for index in sorted(tiles.pictures.values()):
            f.write(f"\to{index}:\n\t\tStart: {index}\n")
    os.makedirs(os.path.join(out, "rules"), exist_ok=True)
    with open(os.path.join(out, "rules", "mapobjects.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(open(os.path.join(ROOT, "tgmc", "rules", "mapobjects.yaml"), encoding="utf-8").read().rstrip("\n") + "\n")
        layer_of = {index: layer for layer, index in tiles.pictures.items()}
        for (picture, hp, blocks, cover), n in tiles.types.items():
            f.write(f"\n{n}:\n\tInherits: {'^MapObjectCover' if cover else '^MapObjectBlocking' if blocks else '^MapObjectOpen'}\n\tHealth:\n\t\tHP: {hp}\n\tWithSpriteBody:\n\t\tSequence: o{picture}\n")
            # A barricade only covers whoever is on the side it faces (the picture's direction: south, north, east, west).
            sheet_path, state, direction = layer_of[picture]
            if cover and "barricade" in (sheet_path + state).lower():
                face_x, face_y = ((0, 1), (0, -1), (1, 0), (-1, 0))[direction if direction < 4 else 0]
                f.write(f"\tBlocksBullets:\n\t\tFaceX: {face_x}\n\t\tFaceY: {face_y}\n")

    # The tileset: the repo's own templates and one per picture
    base = open(os.path.join(ROOT, "tgmc", "tilesets", "ground.yaml"), encoding="utf-8").read().rstrip("\n") + "\n"
    # All templates share one sheet, so it has to be big enough for the repo's own tiles and every picture (32x32 each).
    side = 512
    while (side // 32) ** 2 < (len(tiles.ids) + 16) * 1.15:
        side *= 2
    base = base.replace("SheetSize: 512", f"SheetSize: {side}", 1)
    lines = []
    for key, tid in tiles.ids.items():
        category = {"Rock": "Terrain", "Wall": "Terrain", "ReinforcedWall": "Terrain", "Clear": "Terrain", "Ford": "Water", "Water": "Water"}[tiles.terrain[key]]
        lines += [f"\tTemplate@{tid}:", f"\t\tId: {tid}", f"\t\tImages: tiles/m{tid}.png", "\t\tSize: 1,1", "\t\tPickAny: True",
                  f"\t\tCategories: {category}", "\t\tTiles:", f"\t\t\t0: {tiles.terrain[key]}"]
    os.makedirs(os.path.join(out, "tilesets"), exist_ok=True)
    with open(os.path.join(out, "tilesets", "ground.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(base + "\n".join(lines) + "\n")
    return tiles
