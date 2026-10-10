# TGMC Marines vs Xenos: OpenRA mod (personal, non-commercial)

An [OpenRA](https://github.com/OpenRA/OpenRA) mod that uses sprites and sounds from
[Terra Gov Marine Corps (TGMC)](https://github.com/tgstation/terragov-marine-corps), the
SS13-based game. It has eight units across two factions, plus two xeno structures and a
marine structure set. Each unit has its own weapon, and the NPC bots for each faction train
and send their own units. See [Units and factions](#units-and-factions).

**This repo holds scripts, YAML, and docs only.** No TGMC art or sound, no extracted or
converted sprites or audio, no `.mix`/`.oramap`, and no OpenRA binaries are committed.
The build step makes all of those locally, under `build/`, which is git-ignored.

## Non-commercial use only

The TGMC art and sounds are licensed under Creative Commons NonCommercial terms, and
some are ShareAlike. Use the mod for yourself. Do not sell it, do not host or
redistribute the built mod, and do not publish TGMC-derived art or audio. See
[Licenses](#licenses) below.

## Inputs

| Input | Where | Notes |
| --- | --- | --- |
| TGMC checkout | `https://github.com/tgstation/terragov-marine-corps` | Shallow clone is fine. Use `GIT_LFS_SKIP_SMUDGE=1`. The art is in the repo as plain `.dmi`/`.ogg` files. |
| OpenRA source | `https://github.com/OpenRA/OpenRA` | Targets .NET 10. Build with `make all`. Release builds also work. |
| .NET 10 SDK | Microsoft's package feed | Needed only to build OpenRA. |

The converters read these TGMC files:

- `icons/mob/human.dmi` state `body_m`, with a uniform state from `icons/mob/clothing/uniforms/marine_uniforms.dmi`
  on top, for every marine (`marine_jumpsuit`, `marine_medic`, `marine_engineer`, `marine_assault_crewman`, `pilot_spec`).
- `icons/Xeno/castes/{runner,hunter,spitter,warrior}.dmi`: `Walking`, `Running`, `Dead` states, plus `alien_fire`
  (4 directions, 5 frames) as each caste's attack animation.
- `icons/Xeno/Effects.dmi` state `acidblob`, the spitter's acid glob. `icons/obj/items/grenade.dmi` state `grenade`, the grenadier's shell.
- `icons/Xeno/resin_pod.dmi` (via `mini-silo`), `icons/Xeno/acid_turret.dmi`, and the other structure states listed in `build_sprites.py`.
- `sound/weapons/guns/fire/autorifle-1.ogg` (rifle fire) and `sound/voice/alien/hiss1.ogg` (Runner hiss).
  The new weapons reuse the rifle report and have no sound of their own.

## Layout

```
mod/                        converters and build script (Python 3, Pillow, ffmpeg with libvorbis)
  build_mod.sh              assembles build/mod/tgmc and optionally links it into an OpenRA tree
  tgmc_dmi.py               BYOND .dmi reader: state metadata and frame slicing
  build_sprites.py          .dmi states -> PNG sheets + OpenRA sequence YAML (8 facings)
  build_sounds.py           TGMC .ogg -> mono 22050 Hz Vorbis .ogg
  make_placeholders.py      palette, ground tile, cursor, and a 24x24 test map (no TGMC art)
tgmc/                       the OpenRA mod (YAML and Fluent only)
  mod.yaml                  manifest
  rules/                    world, player, palettes, units, weapons
  tilesets/ground.yaml      one flat ground template
  cursors.yaml, fluent/     cursor names, display strings
build/                      generated; git-ignored
```

The Doom mod in `aliens-vs-predators-with-tgmc-models` is where these converters started.
`tgmc_dmi.py` and the sound converter follow its extractor and sound builder.

## Units and factions

The mod has two factions. Each one's units can only be built by that faction: a build
prerequisite (`ProvidesPrerequisite` in `rules/player.yaml`) grants `marines` or `xenos`,
and every unit lists its faction in `Buildable: Prerequisites`.

| Faction | Unit | Attack | Notes |
| --- | --- | --- | --- |
| Marines | Rifleman | Rifle, 6-cell range, single shot | Standard squad unit |
| Marines | Corpsman (`medic`) | Rifle | No healing yet; 90 HP |
| Marines | Engineer | Rifle | 100 HP |
| Marines | Smartgunner | Rapid spread bullets, 7-cell range, fast reload | Heavy, slow, 130 HP |
| Marines | Grenadier | Lobbed grenade, splash over 2 cells, 8-cell range | Fragile, 90 HP |
| Xenos | Runner | Claws, melee | Fast, 120 HP |
| Xenos | Hunter | Pounce, 2-cell range, very fast | Fastest unit, 110 HP |
| Xenos | Spitter | Acid glob, 6-cell range, splashes on impact | Ranged, slow |
| Xenos | Warrior | Melee slam, 1.5-cell reach, 1.25-cell splash | Tank, 260 HP, slow |

Xenos train their units at the **Resin Pod**, which uses the mini-silo's art and the
Infantry queue. Marines train theirs at the cryo pod and vendor, as before.

**NPC factions.** Each faction has its own bot setup in `rules/player.yaml`, which runs when a
lobby slot is set to the `TGMC AI` bot:

- `UnitBuilderBotModule` per faction. It trains that faction's units in weighted ratios,
  e.g. marines favour riflemen, and xenos favour runners.
- `SquadManagerBotModule` per faction. It gathers squads of 8 and attacks enemy units.
- `GrantConditionOnFaction` gates each module to its own faction, so a marine bot never
  trains xeno units and a xeno bot never trains marines.

The bots have no economy yet. They spend the starting cash of 5000 and then stop producing,
because there are no harvesters and no base-building modules. See [Known gaps](#known-gaps).

## Build and smoke test

Do these in order. Paths are examples.

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

The test field is a 24x24 map with the original marines and runners at facings north,
east, and south, plus one of each new unit and a resin pod. This is the only entry point for now. The mod has no menus
or sidebar yet, so you launch it with `Launch.Map`.

On a headless machine, run OpenRA under Xvfb with Mesa software GL
(`LIBGL_ALWAYS_SOFTWARE=1`). Take screenshots with `xwd -root | convert xwd:- png:out.png`.

## Converter behaviour

- **Sprites.** Each sequence is a stack of `.dmi` states, composited bottom to top. Each unit
  gets one PNG sheet, with cells in `facing * frames + frame` order. The sheet is tagged with
  `FrameSize` and `FrameAmount`, and `sequences/<unit>.yaml` gives `Start`, `Length`, and
  `Facings` for each sequence. OpenRA's facing order is N, NE, E, SE, S, SW, W, NW. TGMC
  provides E and W, so nothing is mirrored (the Doom mod mirrors because its sprites lack
  one side). Diagonals use the side sprite on their own horizontal side: NE and SE use E,
  and SW and NW use W. Xeno castes use their own `alien_fire` for `attack`. Marines have no fire
  frames, so their `attack` reuses `stand`'s cells and no art is duplicated.
- **Duplicate state names.** Some TGMC castes repeat a state name (the hunter has two
  `Hunter Walking` states). BYOND uses the first one, and so does `tgmc_dmi.py`.
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
- Marines have no attack animation. `attack` reuses `stand`. Xeno castes use `alien_fire`. The Runner's
  claws play the hiss on attack.
- Sounds are wired to the rifle (`Report` on `TGMCRifle`, shared by `TGMCSmartgun`) and the Runner's claws
  (hiss). The grenadier, spitter, hunter and warrior are silent. The smoke test doesn't check audio,
  because the headless run has no audio device.
- The NPC bots have no economy. There are no harvesters and no base-building modules, so each bot spends
  its starting cash and then stops producing. Adding income would need a harvester or a cash trickle.
- The new units, the resin pod and the bot setup were checked against OpenRA's source (trait names,
  parameters, sequence and fluent references), not in the game. The `utility.sh --check-yaml` step in
  the smoke test is still the real check.
- The test field uses placeholder terrain (one flat tile). It is not TGMC art.
- The mod has no ingame layout, so there is no sidebar, menu, or order UI yet.
- `Spectator` has no traits, which the YAML checker reports as one intentional warning.
- The Runner's death sound was converted earlier and then dropped. `WithDeathAnimation` has no sound field, so
  wire one in with `Voiced` when you add voice sets.

## Licenses

- **TGMC art and sounds.** These are not in this repo. They are licensed by TGMC, and its
  README lists the terms per asset type: CC-BY-NC (sprites and artwork), CC-BY-NC-SA
  (icons and some sounds), CC-BY-SA (some sprites), and CC-BY (some sounds from FreeSound).
  TGMC's `sound/credits.md` says some of its sounds come from commercial games, and credits
  them that way. The files this mod uses come under those terms. Check the TGMC history for
  the exact licence of any file before you share anything derived from it.
- **TGMC code** is AGPL-3.0 (its `LICENSE`). This mod does not include any TGMC code.
- **OpenRA** is GPL-3.0 (its `COPYING`). The mod loads in OpenRA and is built on it. This
  repo contains no OpenRA code.
- **This repo's scripts and YAML.** No licence has been chosen yet. OpenRA is GPL-3.0, so
  any YAML you distribute with OpenRA should be GPL-compatible.
- **Non-commercial.** Because the TGMC art and sounds are NonCommercial, the built mod is
  for personal use only. Don't redistribute `build/`, its `.oramap` or `.zip` files, or any
  converted sprite or sound.
