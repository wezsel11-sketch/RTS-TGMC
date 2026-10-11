# TGMC Marines vs Xenos: OpenRA mod (personal, non-commercial)

An [OpenRA](https://github.com/OpenRA/OpenRA) mod that uses sprites and sounds from
[Terra Gov Marine Corps (TGMC)](https://github.com/tgstation/terragov-marine-corps), the
SS13-based game. It has marine infantry (rifleman, corpsman, engineer), a xeno Runner, a few
marine and xeno structures, and a TGMC-styled HUD. The xenos have a Runner, a Hunter, an acid-spitting Sentinel and a
structure-mending Drone.

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

- `icons/mob/human.dmi` state `body_m`, with `icons/mob/clothing/uniforms/marine_uniforms.dmi` state `marine_jumpsuit` on top, for the rifleman.
- Terrain tiles: `icons/turf/jungle.dmi` (`grass1`, `grass2`) and `icons/turf/ground_map.dmi` (`dirt`, `seashallow`, `seadeep`).
- `icons/Xeno/castes/hunter.dmi`, `sentinel.dmi` and `drone.dmi` (48px; Hunter and Sentinel have animated walks and runs,
  so each file has a still and an animated state of the same name, and the converter uses the animated one).
- `icons/Xeno/castes/runner.dmi` states `Runner Walking`, `Runner Running`, and `Runner Dead`, for the Runner.
- Marine gear: TGMC's standard marine kit, the unprefixed states, a mottled grey-brown pattern camo: `xarmor` from
  `icons/mob/clothing/suits/marine_armor.dmi`, `marine` boots from `icons/mob/clothing/feet.dmi` (drawn over the armour,
  whose legs would hide them), `helmet` from `marine_helmets.dmi`, and the held weapon from `icons/mob/inhands/guns/`
  (`t18_w` rifle, `m44` pistol, `t19_w` SMG). The corpsman and engineer use the `marine_medic` / `marine_engineer`
  uniform states under the same kit. The `m_` jungle set is darker and hid the marines against the terrain.
- `icons/Xeno/castes/hunter.dmi`, `sentinel.dmi` and `drone.dmi` (48px; Hunter and Sentinel have animated walks and runs,
  so each file has a still and an animated state of the same name, and the converter uses the animated one).
- `icons/Xeno/castes/runner.dmi` states `Runner Walking`, `Runner Running`, and `Runner Dead`, for the Runner.
- Marine gear: TGMC's standard marine kit in jungle camo: `m_xarmor` from `icons/mob/clothing/suits/marine_armor.dmi`,
  `marine` boots from `icons/mob/clothing/feet.dmi` (drawn over the armour, whose legs would hide them), `m_helmet`
  from `marine_helmets.dmi`, and the held weapon from `icons/mob/inhands/guns/` (`t18_w` rifle, `m44` pistol,
  `t19_w` SMG). The corpsman and engineer use the `marine_medic` / `marine_engineer` uniform states under the same kit.
- `icons/Xeno/castes/hunter.dmi`, `sentinel.dmi` and `drone.dmi` (48px; Hunter and Sentinel have animated walks and runs,
  so each file has a still and an animated state of the same name, and the converter uses the animated one).
- `icons/Xeno/castes/runner.dmi` states `Runner Walking`, `Runner Running`, and `Runner Dead`, for the Runner.
- Marine gear: Mark I modular armour from `icons/mob/modular/mark_one/infantry.dmi` (`leg`, `chest`, `arm`, `helm`, tinted
  olive by the converter, since TGMC tints it in code), and the held weapon from `icons/mob/inhands/guns/`
  (`t18_w` rifle, `m44` pistol, `t19_w` SMG). The corpsman and engineer use the `marine_medic` / `marine_engineer`
  uniform states under the same armour.
- Structures: `icons/Xeno/acid_turret.dmi`, `resin_silo.dmi`, `resin_pod.dmi`, and
  `icons/obj/machines/` (`sentry/sentry.dmi`, `cryogenics2.dmi`, `vending.dmi`).
- `sound/weapons/guns/fire/autorifle-1.ogg` (rifle fire) and `sound/voice/alien/hiss1.ogg` (Runner hiss).

## Layout

```
mod/                        converters and build script (Python 3, Pillow, ffmpeg with libvorbis)
  build_mod.sh              assembles build/mod/tgmc and optionally links it into an OpenRA tree
  tgmc_dmi.py               BYOND .dmi reader: state metadata and frame slicing
  build_sprites.py          .dmi states -> PNG sheets + OpenRA sequence YAML (8 facings)
  build_sounds.py           TGMC .ogg -> mono 22050 Hz Vorbis .ogg
  build_tileset.py          TGMC floor tiles (jungle grass, dirt, shallow and deep water) -> 32px PNG tiles
  make_placeholders.py      palette, cursor, clock, fog tiles and the maps (no TGMC art)
  lint_static.py            cross-reference check (sounds, weapons, voice sets, Fluent keys, sequences); build_mod.sh runs it
  smoke.sh                  launches the built mod headless on a map, screenshots it, fails on an engine exception
  test_scenarios.sh         runs the scripted scenario maps (heal, repair, mend, victory, combat, waves, ai, rally) and checks each prints PASS
  balance.sh                runs several AI-vs-AI matches (balance-aivai) in parallel and prints who won and when
  scenarios/                the Lua scripts those maps run (copied into each map by make_placeholders.py)
  check_mod.sh              runs OpenRA's own lint (--check-yaml, --check-missing-sprites) on the built mod and map
  make_chrome.py            HUD atlas (chrome.png) and chrome.yaml: panels, buttons, icons, logo (no TGMC art)
tgmc/                       the OpenRA mod (YAML and Fluent only)
  mod.yaml                  manifest
  rules/                    world, player, palettes, units, structures, weapons
  chrome/                   in-game HUD layouts (player sidebar, observer banner)
  audio/notifications.yaml  UI sound mapping
  tilesets/ground.yaml      one flat ground template
  cursors.yaml, fluent/     cursor names, display strings
build/                      generated; git-ignored
```

The Doom mod in `aliens-vs-predators-with-tgmc-models` is where these converters started.
`tgmc_dmi.py` and the sound converter follow its extractor and sound builder.

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
cd ~/openra-tgmc-mod && OPENRA_DIR=~/openra/openra sh mod/check_mod.sh   # --check-yaml, --check-missing-sprites, and the map

# 5. Launch straight onto the test field. The map UID comes from --map-hash.
MAP=$(sh utility.sh tgmc --map-hash ~/openra-tgmc-mod/build/mod/tgmc/maps/test-field | tail -1)
./launch-game.sh Game.Mod=tgmc Launch.Map=$MAP
```

There are three maps. **Hold the Line** is a survival map: the marines (one human player, no xeno slot) hold their base against
six timed waves of Runners, Hunters and Sentinels coming from the east, and win by destroying the last wave. The script is
`mod/scenarios/wave-survival.lua`; its `Config` table at the top sets the spawn cells, wave sizes and delays.
**Landing Zone** (40x28) is a skirmish map: marines in the west with a cryo pod
and vendor, xenos in the east with a resin silo. Pick a faction in the lobby and build units from the
sidebar palette. Cash comes from a starting amount plus a trickle from the vendor and the silos.
The **test field** is a 24x24 map with three marines and three Runners at facings
north, east, and south, plus a corpsman, an engineer, and one of each structure. The main menu
opens, but the test field is the quickest way in: launch it with `Launch.Map`.

On a headless machine, run OpenRA under Xvfb with Mesa software GL
(`LIBGL_ALWAYS_SOFTWARE=1`). Take screenshots with `xwd -root | convert xwd:- png:out.png`.

## Converter behaviour

- **Sprites.** Each sequence is a stack of `.dmi` states, composited bottom to top. Each unit
  gets one PNG sheet, with cells in `facing * frames + frame` order. The sheet is tagged with
  `FrameSize` and `FrameAmount`, and `sequences/<unit>.yaml` gives `Start`, `Length`, and
  `Facings` for each sequence. Animated states take their timing from the `.dmi` `delay` list:
  `Tick` is the GCD of the delays, and a frame that holds longer is repeated in the sheet
  (the resin silo's 5 s hold becomes 25 repeated cells at a 200 ms tick). OpenRA's facing order is N, NE, E, SE, S, SW, W, NW. TGMC
  provides E and W, so nothing is mirrored (the Doom mod mirrors because its sprites lack
  one side). Diagonals use the side sprite on their own horizontal side: NE and SE use E,
  and SW and NW use W. `attack` reuses `stand`'s cells, so no art is duplicated.
- **Facing check.** Actors placed at facing 0, 256, and 512 show the north (back), east
  (side), and south (front) sprites, as expected.
- **Sounds.** Each `.ogg` is re-encoded to mono, 22050 Hz, Vorbis, and trimmed to 4 seconds.
  OpenRA's `OggLoader` plays them directly.

## Known gaps

- The marine has no death sprite, so it disappears when killed. Its `run` sequence aliases `stand`, because
  TGMC's human sheet has only a standing state.
- Player colour remapping is off. The sprites are RGBA, so the `player` palette doesn't
  recolour them. Units are not coloured by owner.
- Runners have no attack animation. `attack` reuses `stand`. The Runner's claws play the hiss on attack.
- Sounds are wired to weapons (`Report`), voice sets (`audio/voices.yaml`, played on select, order and death)
  and the UI click, deny and ping. The smoke test doesn't check audio, because the headless run has no
  audio device. Structures click when selected and explode on death, with one shared sound.
- Medic and engineer have no heal or repair animation (they reuse `attack`). Healing and repair are weapons
  with negative damage. Scenario tests cover heal, repair, victory and a rifleman-versus-Runner fight.
- Weapons that use `InstantHit` need `TargetActorCenter: true`, or the hit lands on a position and does nothing.
- Terrain is flat tiles from TGMC's `jungle.dmi` and `ground_map.dmi`: grass (two variants), dirt road, a walkable
  ford and impassable water. There are no edge or transition tiles, so shorelines are hard. The test field is all grass.
- The HUD is a command sidebar (radar, production palette with an Infantry and a Xeno tab, requisition, menu button); it reads the same for either faction. There is no selection readout, as that would need C#.
  Production icons are the units' front-facing sprite. The clock overlay and the production tab icons are
  placeholders drawn by the scripts. Production buildings have no rally point yet.
- The AI (`rules/ai.yaml`) only trains units and sends them out in squads. It doesn't build structures.
  Pick "Skirmish AI" for a slot in the lobby.
- The path menu -> Singleplayer -> Skirmish -> lobby (add a Skirmish AI, Start Game) was walked headless and works.
  `tgmc/chrome/mainmenu.yaml` is OpenRA's main menu without the news feed, update notice and forum link.
- Verified by running the mod headless (OpenRA bleed, `mod/check_mod.sh` and `mod/smoke.sh`): the lint passes with
  no errors or warnings, and on Landing Zone the camera starts on the base, the radar and production palette work,
  the vendor spawns queued marines, income ticks up, and a "Skirmish AI" in the xeno slot trains Runners that attack
  the marine base. `mod/test_scenarios.sh` checks heal, repair, mend, victory, combat, the wave script and the AI. The xeno seat was played on Landing Zone against a marine bot: silo, mini silos, all four castes, palette and tooltips work.
  Not yet checked: voices (no audio device).
- AI against AI (`mod/balance.sh`, Landing Zone layout, fastest speed): the marines win about every time, in 2 to 5 minutes
  of game time. The xeno AI masses 12 to 17 units, attacks around minute one, and loses them crossing open ground to
  rifles, sentries and corpsmen before reaching a structure; the marine AI then destroys the hive. The match is never over
  in under two minutes and the loser keeps fighting, but the xenos need a stronger opening. A human xeno player who
  attacks from several sides at once should do better than the AI.
- Hold the Line against a marine bot that holds the base (`mod/balance.sh 4 420 balance-holdline`): the marines win all
  four runs, finishing the last wave (16 Runners, 10 Hunters, 8 Sentinels) with about 30 units and 2 or 3 of their 5
  buildings. The waves attack-move to the marine base because `Hunt()` cannot see across the map for a scripted player.
- Tuning so far: the marine queue takes cost x 60% x 350% ticks (a rifleman is about 8 s) and the xeno queue x 250% (a Runner is about 3 s). Marines have
  120 HP and rifles do 14 every 15 ticks at 6 cells; Runners have 100 HP, run at speed 115 and claws do 20 every 14 ticks;
  Hunters 130 HP; sentries do 10; the corpsman heals 20 every 60 ticks.
  Income is 15 cash every 2 s from the vendor and silo and 5 from a mini silo. None of this has had real play time.
- Fog of war is drawn with plain black quadrant tiles, so edges look blocky.
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
