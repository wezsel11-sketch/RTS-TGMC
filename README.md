# TGMC Marines vs Xenos: OpenRA mod (personal, non-commercial)

An [OpenRA](https://github.com/OpenRA/OpenRA) mod that uses sprites and sounds from
[Terra Gov Marine Corps (TGMC)](https://github.com/tgstation/terragov-marine-corps), the
SS13-based game. It has marine infantry (rifleman, corpsman, engineer, smartgunner, grenadier), a few
marine and xeno structures, and a TGMC-styled HUD. The xenos have a Runner, a Hunter, an acid-spitting Sentinel, a
structure-mending Drone and a heavy Warrior.

**This repo holds scripts, YAML, and docs only.** No TGMC art or sound, no extracted or
converted sprites or audio, no `.mix`/`.oramap`, and no OpenRA binaries are committed.
The build step makes all of those locally, under `build/`, which is git-ignored.

## Non-commercial use only

The TGMC art and sounds are licensed under Creative Commons NonCommercial terms, and
some are ShareAlike. Use the mod for yourself. Do not sell it, do not host or
redistribute the built mod, and do not publish TGMC-derived art or audio. See
[Licenses](#licenses) below.

## Quick start

You need `git`, `make`, `python3` with Pillow, `ffmpeg` (with libvorbis) and a POSIX shell. Linux and macOS work; on Windows use WSL.
No .NET? The script installs a .NET 10 SDK into `build/tools`, and nothing outside `build/` is touched.

```sh
git clone -b claude/hopeful-heisenberg-6kyjk9 https://github.com/wezsel11-sketch/RTS-TGMC.git
cd RTS-TGMC
sh mod/setup.sh      # fetches OpenRA and the TGMC art, builds and checks the mod (about 10 minutes the first time)
sh mod/play.sh       # main menu; or `sh mod/play.sh landing-zone` to jump straight into a map
```

`setup.sh` is safe to re-run: it skips finished steps and picks up changes to the converters. It pins OpenRA and TGMC to
the commits this mod was tested against (see the top of the script), so a later change in either cannot break it.

## How to play

- **Main menu -> Singleplayer -> Skirmish.** Pick **Landing Zone** (two-player skirmish) or **Hold the Line** (marines against waves).
  In Landing Zone choose a faction for yourself and set the other slot to **Skirmish AI**, then Start Game.
- **Marines** start with a cryo pod, a vendor and a squad. Click the cryo pod and use the sidebar's *Infantry* tab to train riflemen,
  corpsmen (they heal), engineers (they repair), smartgunners (rapid spread fire) and grenadiers (splash). **Xenos** start with a resin silo and mini silos; use the *Xeno* tab for Runner,
  Hunter, Sentinel (spits acid), Drone (mends structures) and Warrior (wide melee slam).
- **Cash** is a starting sum plus a trickle from the vendor and the silos. There is no harvesting.
- **Controls** are OpenRA's: left-click or drag to select, right-click to move or attack, `A` then click to attack-move,
  `S` to stop, `Ctrl`+number to group, and right-click a production building to set where new units gather (rally point).
  The game speed option "fastest" is the one the balance tests ran at.
- **Win** by destroying every enemy structure and unit that counts (Conquest). In Hold the Line you win by destroying the
  sixth wave and lose when your units are gone.

What to try and report: whether the sounds are the right loudness and mix (this is the first time anyone hears them), whether
a match feels fair from either side (the AI-vs-AI tests say the marines win easily), and anything that looks or behaves oddly.
Logs and replays are in OpenRA's support directory (`~/.config/OpenRA` on Linux, `~/Library/Application Support/OpenRA` on macOS).

## Inputs

| Input | Where | Notes |
| --- | --- | --- |
| TGMC checkout | `https://github.com/tgstation/terragov-marine-corps` | `setup.sh` makes a sparse, blob-less clone. A shallow clone is fine too. Use `GIT_LFS_SKIP_SMUDGE=1`. The art is in the repo as plain `.dmi`/`.ogg` files. |
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
- Structures: `icons/Xeno/acid_turret.dmi`, `resin_silo.dmi`, `resin_pod.dmi`, and
  `icons/obj/machines/` (`sentry/sentry.dmi`, `cryogenics2.dmi`, `vending.dmi`).
- About 150 sound clips (weapons, voices, announcer, music, ambience), listed in `SOUNDS` in `mod/build_sounds.py`.

The exact list is `python3 mod/tgmc_paths.py`; `setup.sh` checks out only those files.

## Layout

```
mod/                        converters and build script (Python 3, Pillow, ffmpeg with libvorbis)
  setup.sh                  one-command bootstrap: OpenRA, TGMC art (sparse clone), mod build, lint
  play.sh                   starts the game on the main menu or a map
  tgmc_paths.py             lists the TGMC files the converters read (setup.sh sparse-checks out exactly these)
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

## Build by hand

`mod/setup.sh` does all of this. The steps are here for a different layout (your own OpenRA checkout, a full TGMC clone). Paths are examples.

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
- **Sounds.** `build_sounds.py` converts about 150 TGMC clips. Each is re-encoded to Vorbis and scaled so its loudest
  sample sits at a peak chosen for its kind (weapons and voices -3 dB, interface -9, announcer -6, ambience -16, music -6),
  and trimmed to a per-kind length with a short fade. Effects and voices are mono 22 kHz; music is stereo 44.1 kHz.
  The levels are numbers, not a mix anyone has heard. OpenRA's `OggLoader` plays them directly.
  The `audio` folder is mounted as its own package in `mod.yaml`, so sounds are referred to by bare file name
  (`rifle-fire-1.ogg`). OpenRA's file index lists only the top level of a mounted package, so a sound in a sub-folder
  silently fails to load; the sound log reports it as "file does not exist".

## Sound

- **Marines** have a male and a female recording of every voice clip, and each marine keeps one voice (picked by actor id
  through the voice set's `Prefixes`). Select, move, attack and death each have their own pool: warcries, grenade shouts,
  screams and gored cries. The corpsman says "medic" when selected.
- **Xenos** have a voice set per caste. Runner: small shrieks and pounces. Hunter: growls and heavy roars, with the long
  death scream. Sentinel: talking, hisses and its spit. Drone: chatter and cries for help.
- **Hits.** Rifles thud on aliens and structures, and now and then an alien cries out; claws thud on armour and marines
  cry out (`Human` and `Alien` target types pick which). Acid splashes on impact.
- **Structures** click when selected; marine ones explode when destroyed and hive ones break up with a resin crack.
  The cryo pod and vendor hum, and a cave ambience plays across the map with long gaps.
- **Announcer** (the ship's AI, ARES): game start, unit ready, queue and refusal pings, a siren when a building is attacked,
  an alert when a unit is lost, code red and a distress beacon for Hold the Line waves, and win and lose stings.
- **Music** is TGMC's four theme tracks (`neutral_hopeful` and `neutral_melancholy`). They run 10 to 20 seconds each, so
  the playlist is about a minute long and repeats a lot; TGMC has no longer music.
- `mod/lint_static.py` checks every sound name against `build_sounds.py`, including each clip of each prefixed voice set.
  `scenario-sounds` plays every sound, announcer line and track, and `test_scenarios.sh` fails any scenario whose
  `sound.log` says a file did not load. None of it has been heard: this machine has no audio device.

## Known gaps

- The marine has no death sprite, so it disappears when killed. Its `run` sequence aliases `stand`, because
  TGMC's human sheet has only a standing state.
- Player colour remapping is off. The sprites are RGBA, so the `player` palette doesn't
  recolour them. Units are not coloured by owner.
- Runners have no attack animation. `attack` reuses `stand`. The Runner's claws play the hiss on attack.
- Sounds are all unheard (no audio device here). See the Sound section.
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
- `mod/setup.sh` was run from an empty directory on a fresh clone (it installed .NET, built OpenRA, made the sparse TGMC clone, built
  and linted the mod in about two minutes on a fast connection); a second run skipped the finished steps, and the scenarios, the smoke test
  and `play.sh hold-the-line` all ran afterwards. Only Linux x64 has been tried. macOS and WSL are untested.
- Fog of war is drawn with plain black quadrant tiles, so edges look blocky.

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
