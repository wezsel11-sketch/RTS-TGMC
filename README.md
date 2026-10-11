# TGMC Marines vs Xenos: OpenRA mod (personal, non-commercial)

An [OpenRA](https://github.com/OpenRA/OpenRA) mod that uses sprites and sounds from
[Terra Gov Marine Corps (TGMC)](https://github.com/tgstation/terragov-marine-corps), the
SS13-based game. It has marines (rifleman, corpsman, engineer), a xeno Runner, and a few
marine and xeno structures.

## Play

Windows 10 or 11, 64-bit. Nothing to install.

1. `git clone` this repo.
2. Double-click `PLAY.cmd`.

The first launch shows two one-time setup screens (player name and controls, then an opt-in
for sending system info to OpenRA; it is off unless you tick it). Then pick **Singleplayer**,
**Skirmish**, and **Start Game**. The lobby offers the "TGMC test field" map. Settings, logs and screenshots go in
`game/Support/`, so the folder is portable. If the game exits with an error, `PLAY.cmd` shows
the log folder.

`game/` is a self-contained OpenRA build (.NET runtime and native SDL2, OpenAL, FreeType and Lua
libraries included) with the converted TGMC mod already in `game/mods/tgmc`. Windows SmartScreen
may warn about the unsigned `OpenRA.exe`; choose "Run anyway". The engine is built from
[OpenRA commit `e7e9e4a`](https://github.com/OpenRA/OpenRA/commit/e7e9e4ad270221d7fb9725b348c75504d48c1ebd),
pinned in `mod/OPENRA_REF`.

## Private repo, non-commercial use only

This repo commits the converted TGMC art and sound and the OpenRA binaries so that a clone
runs as is. That is only OK while the repo stays **private** and the game stays **personal**.
The TGMC art and sounds are licensed under Creative Commons NonCommercial terms, and some are
ShareAlike. Do not make this repo public, sell the game, or share `game/` or any converted
sprite or sound with anyone else. See [Licenses](#licenses) below.

## Rebuilding `game/`

You only need this to change the mod art, the rules, or the engine version. Edit `tgmc/` (YAML) or
`mod/` (converters), then run, on Linux or macOS:

```sh
sh mod/package_windows.sh     # or: TGMC=~/tgmc sh mod/package_windows.sh
```

It fetches OpenRA at `mod/OPENRA_REF`, cross-publishes a self-contained win-x64 build into `game/`,
rebuilds the mod from a shallow TGMC clone, and copies it to `game/mods/tgmc`. `game/Support/` is
left alone. Commit the result. It needs git, curl, Python 3 with Pillow, and ffmpeg with libvorbis.
It installs a .NET 10 SDK under `build/dotnet` if `dotnet` is not on PATH.

## Inputs (for rebuilding)

| Input | Where | Notes |
| --- | --- | --- |
| TGMC checkout | `https://github.com/tgstation/terragov-marine-corps` | Shallow clone is fine. Use `GIT_LFS_SKIP_SMUDGE=1`. The art is in the repo as plain `.dmi`/`.ogg` files. |
| OpenRA source | `https://github.com/OpenRA/OpenRA` | Targets .NET 10. Build with `make all`. Release builds also work. |
| .NET 10 SDK | Microsoft's package feed | Needed only to build OpenRA. |

The converters read these TGMC files:

- `icons/mob/human.dmi` state `body_m`, with `icons/mob/clothing/uniforms/marine_uniforms.dmi` state `marine_jumpsuit` on top, for the rifleman.
- `icons/Xeno/castes/runner.dmi` states `Runner Walking`, `Runner Running`, and `Runner Dead`, for the Runner.
- `sound/weapons/guns/fire/autorifle-1.ogg` (rifle fire) and `sound/voice/alien/hiss1.ogg` (Runner hiss).

## Layout

```
mod/                        converters and build script (Python 3, Pillow, ffmpeg with libvorbis)
  package_windows.sh        builds game/ (engine + mod) for Windows x64
  OPENRA_REF                the pinned OpenRA commit
  build_mod.sh              assembles build/mod/tgmc; optionally links it into an OpenRA tree or copies it to INSTALL_TO
  tgmc_dmi.py               BYOND .dmi reader: state metadata and frame slicing
  build_sprites.py          .dmi states -> PNG sheets + OpenRA sequence YAML (8 facings)
  build_sounds.py           TGMC .ogg -> mono 22050 Hz Vorbis .ogg
  make_placeholders.py      palette, ground tile, cursor, and a 24x24 test map (no TGMC art)
tgmc/                       the OpenRA mod (YAML and Fluent only)
  mod.yaml                  manifest
  rules/                    world, player, palettes, units, weapons
  tilesets/ground.yaml      one flat ground template
  cursors.yaml, fluent/     cursor names, display strings
PLAY.cmd                    double-click launcher for game/
game/                       the ready-to-run game (committed): OpenRA win-x64, mods/common, mods/tgmc
build/                      scratch space for package_windows.sh; git-ignored
```

The Doom mod in `aliens-vs-predators-with-tgmc-models` is where these converters started.
`tgmc_dmi.py` and the sound converter follow its extractor and sound builder.

## Developer build and smoke test (Linux)

This is the from-source path for development and headless checks. Do these in order. Paths are examples.

```sh
# 1. Build OpenRA from source (needs the .NET 10 SDK)
git clone --depth 1 https://github.com/OpenRA/OpenRA ~/openra/openra
cd ~/openra/openra && make all

# 2. Shallow-clone TGMC without LFS objects
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://github.com/tgstation/terragov-marine-corps ~/tgmc

# 3. Assemble the mod. OPENRA_DIR is optional; it links build/mod/tgmc into OpenRA's mods/ folder.
cd ~/openra-tgmc-mod
TGMC=~/tgmc OPENRA_DIR=~/openra/openra sh mod/build_mod.sh

# 4. Check the YAML (run from the OpenRA folder)
cd ~/openra/openra && sh utility.sh tgmc --check-yaml          # expect 0 errors, 1 warning
sh utility.sh tgmc --check-missing-sprites                      # prints the mod name and no errors

# 5. Launch straight onto the test field. The map UID comes from --map-hash.
MAP=$(sh utility.sh tgmc --map-hash ~/openra-tgmc-mod/build/mod/tgmc/maps/test-field | tail -1)
./launch-game.sh Game.Mod=tgmc Launch.Map=$MAP
```

The test field is a 24x24 map with marines, Runners and a few structures at facings
north, east, and south. `Launch.Map` starts it directly, skipping the menu.

On a headless machine, run OpenRA under Xvfb with Mesa software GL
(`LIBGL_ALWAYS_SOFTWARE=1`). Take screenshots with `xwd -root | convert xwd:- png:out.png`.

## Converter behaviour

- **Sprites.** Each sequence is a stack of `.dmi` states, composited bottom to top. Each unit
  gets one PNG sheet, with cells in `facing * frames + frame` order. The sheet is tagged with
  `FrameSize` and `FrameAmount`, and `sequences/<unit>.yaml` gives `Start`, `Length`, and
  `Facings` for each sequence. OpenRA's facing order is N, NE, E, SE, S, SW, W, NW. TGMC
  provides E and W, so nothing is mirrored (the Doom mod mirrors because its sprites lack
  one side). Diagonals use the side sprite on their own horizontal side: NE and SE use E,
  and SW and NW use W. `attack` reuses `stand`'s cells, so no art is duplicated.
- **Facing check.** Actors placed at facing 0, 256, and 512 show the north (back), east
  (side), and south (front) sprites, as expected.
- **Sounds.** Each `.ogg` is re-encoded to mono, 22050 Hz, Vorbis, and trimmed to 4 seconds.
  OpenRA's `OggLoader` plays them directly.

## Known gaps

- The marine has no death sprite, so it disappears when killed. Its `run` sequence uses the same
  art as `stand`, duplicated in the sheet, because TGMC's human sheet has only a standing state.
- The marine's worn gear is the jumpsuit only. Helmets, armour, and held weapons aren't drawn.
- Player colour remapping is off. The sprites are RGBA, so the `player` palette doesn't
  recolour them. Units are not coloured by owner.
- Runners have no attack animation. `attack` reuses `stand`. The Runner's claws play the hiss on attack.
- Sounds are wired to the rifle (`Report` on `TGMCRifle`) and the Runner's claws (hiss). The smoke test
  doesn't check audio, because the headless run has no audio device.
- The test field uses placeholder terrain (one flat tile). It is not TGMC art.
- The ingame HUD is a stub: a selection panel and a requisition counter, with no build sidebar or order UI yet.
- `Spectator` has no traits, which the YAML checker reports as one intentional warning.
- The Runner's death sound was converted earlier and then dropped. `WithDeathAnimation` has no sound field, so
  wire one in with `Voiced` when you add voice sets.

## Licenses

- **TGMC art and sounds.** The converted sprites and sounds are in `game/mods/tgmc` (private repo only). They are licensed by TGMC, and its
  README lists the terms per asset type: CC-BY-NC (sprites and artwork), CC-BY-NC-SA
  (icons and some sounds), CC-BY-SA (some sprites), and CC-BY (some sounds from FreeSound).
  TGMC's `sound/credits.md` says some of its sounds come from commercial games, and credits
  them that way. The files this mod uses come under those terms. Check the TGMC history for
  the exact licence of any file before you share anything derived from it.
- **TGMC code** is AGPL-3.0 (its `LICENSE`). This mod does not include any TGMC code.
- **OpenRA** is GPL-3.0 (its `COPYING`, copied to `game/COPYING`). `game/` holds an unmodified OpenRA
  build; its source is the commit in `mod/OPENRA_REF`. If you ever share `game/`, the GPL needs you to
  offer that source with it.
- **This repo's scripts and YAML.** No licence has been chosen yet. OpenRA is GPL-3.0, so
  any YAML you distribute with OpenRA should be GPL-compatible.
- **Non-commercial.** Because the TGMC art and sounds are NonCommercial, the built mod is
  for personal use only. Keep the repo private. Don't redistribute `game/`, `build/`, or any
  converted sprite or sound.
