"""Print every TGMC file the converters read, one repo-relative path per line.

The list is derived from build_sprites.UNITS, build_sounds.SOUNDS and build_tileset.TILES, so a new sprite, sound
or tile cannot be left out of the sparse checkout that setup.sh makes. Use it with
`git sparse-checkout set --no-cone --stdin`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_sounds  # noqa: E402
import build_sprites  # noqa: E402
import build_tileset  # noqa: E402


def paths():
    found = set()
    for unit in build_sprites.UNITS.values():
        for layers in unit["sequences"].values():
            if isinstance(layers, str):
                continue  # alias of another sequence, no new art
            if isinstance(layers, dict):
                layers = layers["fall"]  # a generated fall sequence: it reads the layers of its stand pose
            for layer in layers:
                found.add(layer[0])
    for entry in build_sounds.SOUNDS.values():
        found.add(entry[0])
    for entry in build_tileset.TILES.values():
        found.add(entry[0])
    return sorted(found)


if __name__ == "__main__":
    print("\n".join(paths()))
