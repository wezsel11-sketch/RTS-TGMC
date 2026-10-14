"""Print every TGMC file the converters read, one repo-relative path per line.

The list is derived from build_sprites.UNITS, build_sounds.SOUNDS, build_tileset.TILES and tgmc_dmm.MAPS, so a new sprite, sound
or tile cannot be left out of the sparse checkout that setup.sh makes. Use it with
`git sparse-checkout set --no-cone --stdin`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_sounds  # noqa: E402
import build_sprites  # noqa: E402
import build_tileset  # noqa: E402
import tgmc_dmm  # noqa: E402


def paths():
    found = set()
    for unit in build_sprites.UNITS.values():
        for layers in unit["sequences"].values():
            if isinstance(layers, str):
                continue  # alias of another sequence, no new art
            for layer in layers:
                found.add(layer[0])
                if len(layer) > 3 and isinstance(layer[3].get("or_sheet"), str):
                    found.add(layer[3]["or_sheet"])  # the left-hand sheet of a two-handed gun
    for entry in build_sounds.SOUNDS.values():
        if not entry[0].startswith(build_sounds.OPEN_PREFIX):  # the open music is downloaded, not read from TGMC
            found.add(entry[0])
    for entry in build_tileset.TILES.values():
        found.add(entry[0])
    found.update(tgmc_dmm.paths())
    found.update(build_sprites.CONDOR_FILES)
    return sorted(found)


if __name__ == "__main__":
    print("\n".join(paths()))
