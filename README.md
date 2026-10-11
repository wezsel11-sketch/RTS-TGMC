# TGMC Marines vs Xenos: OpenRA mod (personal, non-commercial)

An [OpenRA](https://github.com/OpenRA/OpenRA) mod that uses sprites and sounds from
[Terra Gov Marine Corps (TGMC)](https://github.com/tgstation/terragov-marine-corps), the
SS13-based game. It has marine infantry (rifleman, corpsman, engineer, smartgunner, grenadier, mortar crew), an assault mech,
marine and xeno structures you build from a Build menu (supply generators, walls, tech, research), and a TGMC-styled HUD. The xenos have a Runner, a Hunter, an
acid-spitting Sentinel, a structure-mending Drone, a heavy Warrior, a Queen, a Boiler for artillery and a Crusher for armour. Units rank up, have abilities, and
show their wounds; one map is TGMC's own LV-624.

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
git clone -b claude/optimistic-volta-3p3z2y https://github.com/wezsel11-sketch/RTS-TGMC.git
cd RTS-TGMC
sh mod/setup.sh      # fetches OpenRA and the TGMC art, builds and checks the mod (about 10 minutes the first time)
sh mod/play.sh       # main menu; or `sh mod/play.sh landing-zone` to jump straight into a map
```

`setup.sh` is safe to re-run: it skips finished steps and picks up changes to the converters. It pins OpenRA and TGMC to
the commits this mod was tested against (see the top of the script), so a later change in either cannot break it.

## How to play

- **Main menu -> Singleplayer -> Skirmish.** Pick **Landing Zone** or **LV-624** (two-player skirmishes) or **Hold the Line** (marines against waves).
  Choose a faction for yourself and set the other slot to a **Skirmish AI** (Easy, Normal or Hard), then Start Game. **LV-624** is TGMC's own map
  of that name, cropped to the landing zone (marines) and the central caves (xenos), with the river between them.
- **Marines** start with a cryo pod, a vendor and a squad. Click the cryo pod and use the sidebar's *Infantry* tab to train riflemen,
  corpsmen (they heal), engineers (they repair), smartgunners (rapid spread fire) and grenadiers (splash). **Xenos** start with a resin silo and mini silos; use the *Xeno* tab for Runner,
  Hunter, Sentinel (spits acid), Drone (mends structures) and Warrior (wide melee slam).
- **Building.** Both factions have a **Build** tab (the third button beside the production palette). Click a structure to queue
  it; when its clock finishes, click its icon again and place it on the map. You can only place within 5 cells of a *builder*,
  so send one to the site first (its build range is shown while you place):
  - **Marines**: an **Engineer** builds everything.
  - **Xenos**: a **Drone** builds minor structures (Weed Node, Resin Wall, Resin Turret); the **Queen** builds those and the big
    ones too (Evolution and Maturity Towers, Silos). Train the Queen from a Resin Silo (one at a time); a match starts with one.
    The Build tab is gone while you have no builder, so keep a spare. Walls are dragged: place one end, then the other.
- **Tech.** Better units need a structure first:

  | Marines | Needs | Xenos | Needs |
  | --- | --- | --- | --- |
  | Smartgunner, Sentry Turret | Armory | Hunter, Sentinel, Resin Turret | Evolution Tower |
  | Grenadier, Mortar Crew | Ordnance Depot (needs an Armory) | Warrior, Crusher, Boiler | Maturity Tower (needs an Evolution Tower) |
  | Assault Mech | Mech Bay (needs an Ordnance Depot) | Hive Core (research) | Evolution Tower |
  | Research Lab (research, Orbital Strike) | Armory | Rifleman, Corpsman, Engineer | nothing |
  | Runner, Drone | nothing | | |

- **Armour and artillery.** The Crusher and the Assault Mech have *Heavy* armour: rifles and claws do about a third of their damage to it,
  while the mech's cannon, the Boiler's acid, the mortar and acid in general do full damage or more. The Crusher tramples marines it walks over.
  The **Mortar Crew** (marines) and the **Boiler** (xenos) are artillery: long range, wide splash, frail, and they back away from
  anything inside their minimum range (three and four cells) to get a shot.
- **Research.** A **Research Lab** gives every marine 15% less damage taken and 10% more damage dealt and unlocks the **Orbital Strike**; a
  **Hive Core** gives every xeno 15% less damage taken and 8% more speed.
- **Weeds.** Xenos near a Weed Node or a silo move 25% faster and heal slowly.
- **Ranks.** Units earn experience for kills, in proportion to the victim's cost, and rank up three times. Each rank adds damage, takes less damage, and
  the third adds speed and slow healing. Rank chevrons show under the unit. Xenos need fewer kills per rank than marines.
- **Abilities.** Press `F` (deploy) with a unit selected, or use the support power icons above the readout:

  | Ability | Who | What it does |
  | --- | --- | --- |
  | Pounce | Runner | Three seconds of sprinting; the claws hit harder and stun a marine. 20 s to recharge. |
  | Stealth | Hunter | Eight seconds invisible. An attack or a hit gives it away; sentries and marines within two cells see it. |
  | Screech | Queen (support power) | Marines within five cells of the target are slowed and shoot half as fast for seven seconds. |
  | Flare | Marines (support power, needs an Armory) | Lights up the ground round the target for twelve seconds. |
  | Orbital Strike | Marines (support power, needs a Research Lab) | A heavy blast lands on the marked spot a moment later. Friendly fire is off. |

- **Supplies.** The vendor and silos now give only a small trickle. The real income is the **Miner** (marines) and the
  **Weed Node** (xenos), up to six of each. **Cade** (marines) and **Resin Wall** (xenos) are the cheap walls.
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
- Structures: `icons/Xeno/acid_turret.dmi`, `resin_silo.dmi`, `resin_pod.dmi`, `weeds.dmi` (Weed Node), `2x2building.dmi` (Evolution
  and Maturity Towers), `icons/obj/smooth_objects/resin-wall.dmi`, and `icons/obj/` (`mining_drill.dmi` for the Miner,
  `structures/barricades/metal.dmi` for the Cade, `machines/` `sentry/sentry.dmi`, `cryogenics2.dmi`, `vending.dmi` for the Vendor, Armory
  and Ordnance Depot). The Queen is `icons/Xeno/castes/queen.dmi`.
- `icons/Xeno/castes/crusher.dmi` and `boiler.dmi` (Crusher, Boiler), `icons/mecha/mech_medium.dmi` (the mech, five parts composited), `icons/obj/machines/deployable/mortar.dmi`
  (the mortar beside a marine for the mortar crew), `icons/mecha/mech_bay.dmi` (Mech Bay), `vending.dmi` states for the Research Lab, `2x2building.dmi` `orb_idle` (Hive Core),
  `icons/effects/effects.dmi` and `96x96.dmi` smoke for damaged structures, and `_maps/map_files/LV624/LV624.dmm` with the wall and floor sheets for its terrain.
- About 150 sound clips (weapons, voices, announcer, music, ambience; about 200 with the full music set), listed in `SOUNDS` in `mod/build_sounds.py`.

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
  build_tileset.py          TGMC floor and wall tiles (grass, dirt, water, rock, jungle, walls, floors) -> 32px PNG tiles, with optional tint and edge
  build_map.py              TGMC's LV624.dmm -> the LV-624 skirmish map and its AI-vs-AI copy
  make_placeholders.py      palette, cursor, clock, fog tiles and the maps (no TGMC art)
  lint_static.py            cross-reference check (sounds, weapons, voice sets, Fluent keys, sequences); build_mod.sh runs it
  smoke.sh                  launches the built mod headless on a map, screenshots it, fails on an engine exception
  test_scenarios.sh         runs the scripted scenario maps and checks each prints PASS (heal, repair, mend, victory, combat, fx, waves, ai and its three strengths, rally, build,
                            sounds, death, ruin, vet, abilities, armor, artillery, research on and off, weeds, orbital); SCENARIO_ONLY="death vet" runs a few
  balance.sh                runs several AI-vs-AI matches (balance-aivai) in parallel and prints who won and when
  scenarios/                the Lua scripts those maps run (copied into each map by make_placeholders.py)
  check_mod.sh              runs OpenRA's own lint (--check-yaml, --check-missing-sprites) on the built mod and map
  make_chrome.py            TGUI-style UI atlas (olive, slate, amber) and chrome.yaml: windows, tabs, panels, icons, logo (no TGMC art)
tgmc/                       the OpenRA mod (YAML and Fluent only)
  mod.yaml                  manifest
  rules/                    world, player, palettes, units, structures, weapons
  chrome/                   in-game HUD layouts (player sidebar, observer banner)
  audio/notifications.yaml  UI sound mapping
  audio/music.yaml          the playlist: themes, tense tracks, lobby theme, ambience loops
  scripts/music.lua         faction-aware, fight-aware music (the world's LuaScript)
  tilesets/ground.yaml      one flat ground template
  cursors.yaml, fluent/     cursor names, display strings
  chrome/                   main menu, Esc menu, in-game sidebar and observer banner (TGUI-style)
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

There are four maps (the LV-624 map is built by `build_map.py`; see Known gaps). **Hold the Line** is a survival map: the marines (one human player, no xeno slot) hold their base against
six timed waves of Runners, Hunters and Sentinels coming from the east, and win by destroying the last wave. The script is
`mod/scenarios/wave-survival.lua`; its `Config` table at the top sets the spawn cells, wave sizes and delays.
**Landing Zone** (40x28) is a skirmish map: marines in the west with a cryo pod
and vendor, xenos in the east with a resin silo. Pick a faction in the lobby and build units from the
sidebar palette. Cash comes from a starting amount, a small trickle from the vendor and the silos, and the Miners and Weed Nodes you build.
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
  sample sits at a peak chosen for its kind (weapons and voices -3 dB, interface -9, announcer -6, ambience -16, music -6, ambience-as-music -12),
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
- **Music** is every music track TGMC has, plus its ambience loops as a calm backdrop. TGMC's real music is short: the
  four neutral themes (10 to 20 s), two tense themes (`nuclear_detonation`), the dread theme (`zombies_loss`), the elevator
  track and the lobby theme (the only long one, about three minutes). Win and loss stings are not in the playlist. The 40
  ambience loops (`ambigen`, `ambicha`, `ambisin`, `ambilava`, `ambicave` and others, capped at 75 s) are stereo music
  at -12 dB. All of it is in `tgmc/audio/music.yaml`.
  `tgmc/scripts/music.lua` plays it, because OpenRA's playlist cannot filter by faction. **Marines** get the hopeful themes,
  elevator, lobby and station ambience; **xenos** get the melancholy and dread themes and the cave, lava and jungle
  ambience; an observer gets a bit of both. A theme and an ambience track alternate. When an enemy comes within 8 cells of
  one of your units or structures the tense tracks take over, and the calm ones return about 30 s after the fight.
  The script is the world's `LuaScript`; a map with its own script (Hold the Line) lists it last. After the in-game
  next/previous keys, OpenRA's own shuffled playlist (all tracks) continues. `mod/lint_static.py` checks every track
  named in the script and playlist.
- `mod/lint_static.py` checks every sound name against `build_sounds.py`, including each clip of each prefixed voice set.
  `scenario-sounds` plays every sound, announcer line and track, and `test_scenarios.sh` fails any scenario whose
  `sound.log` says a file did not load. None of it has been heard: this machine has no audio device.

## Effects

The effect sprites are TGMC art too (`fx-*` images in `build_sprites.py`) and are named by `tgmc/rules/weapons.yaml`:

- **Guns spit bullets.** Rifle, smartgun and sentry shots fly as turned tracers (16 facings, the sentry's is heavier).
  Riflemen, smartgunners and the sentry flash at the muzzle (`WithMuzzleOverlay`, sequence `flash` on the unit's own sheet).
  Hits throw sparks on structures and acid-green gore on xenos.
- **Grenadiers carry a grenade launcher.** It thumps (`grenadelauncher.ogg`) with a puff of smoke at the muzzle, lobs the
  grenade on its arc and explodes with a fireball that fades into smoke, plus an explosion sound.
- **Xenos spit acid.** The Sentinel and the resin turret fire a visible acid glob (a fast arc, with a wide enough splash to
  land on a walking marine), which splashes green on impact.
- **Melee and support hits.** Claws draw blood on marines and sparks on structures; the Warrior's slam kicks up a dust
  shockwave; the corpsman's heal sparkles, the engineer's repair sparks and the drone's mend sparkles.
- `mod/lint_static.py` checks each weapon's image and sequence names and each `MuzzleSequence`.

## Known gaps

- Marines have no run or attack frames: `run` and `attack` alias `stand`, because TGMC's human sheet has only a standing state. They do
  fall over and leave a corpse when killed: TGMC has no marine death art, so `mod/build_sprites.py` turns the standing pose onto its
  back over five frames and adds a pool of blood (the `fall` sequence spec). The same goes for the mortar crew.
- Owner colour is a ring under each unit and a plate on each structure, not a recolouring of the unit: the TGMC sprites are RGBA and cannot be
  remapped, so `mod/make_placeholders.py` draws indexed ring and plate sprites in the player-colour palette range, which the engine recolours.
- The marine wounds (blood at 75%, 50% and 25% health, a limp at 25%) are drawn splotches (`wounds.png`), the same whichever way the marine faces.
- Runners have no attack animation. `attack` reuses `stand`. The Runner's claws play the hiss on attack.
- Sounds are all unheard (no audio device here). See the Sound section.
- Medic and engineer have no heal or repair animation (they reuse `attack`). Healing and repair are weapons
  with negative damage. Scenario tests cover heal, repair, victory and a rifleman-versus-Runner fight.
- Weapons that use `InstantHit` need `TargetActorCenter: true`, or the hit lands on a position and does nothing.
- Acid is now a projectile, so a fast runner can still outrun a glob. Effects have not been tuned by eye in a long match.
- Terrain is flat tiles from TGMC's `jungle.dmi`, `ground_map.dmi`, `walls/cave.dmi`, `walls/junglewall.dmi` and `floors.dmi`: grass (two
  variants), dirt road, cave floor, colony floors, a walkable ford, and impassable water, rock, dense jungle and walls. There are no edge or
  transition tiles, so shorelines and cave edges are hard. The test field is all grass.
- **LV-624** (`mod/build_map.py`) reads TGMC's own `LV624.dmm` (220 x 180 cells), crops the second landing zone and the central caves plus a margin
  (67 x 116 cells), and maps each turf to one of the mod's terrain tiles. Only turfs, windows, trees and catwalks are read; other objects (fences,
  tables, vines, doors) are ignored, so the colony reads as open floor with its walls and windows kept. The marines start on the landing pad;
  the xenos start in the roomiest cave cell, not in TGMC's xeno spawner room (a small walled closet at the cave's edge). A flood fill checks that
  the two bases are connected; if water or walls ever cut them apart the converter carves a route and says so. `balance-lv624` is the same ground
  with a bot on each side (`mod/balance.sh 4 600 balance-lv624`).
- The HUD is a command sidebar (radar, production palette with an Infantry, Xeno and Build tab, a row of support power icons, requisition, menu
  button); it reads the same for either faction. Units and structures now show a selection box and a health bar (when selected, or per the
  Settings -> Game "status bars" option), and the engine's own Deploy key (`F` by default) drives the Runner's Pounce and the Hunter's Stealth. There is no
  selection readout of stats, as that would need C#. Production icons are the units' front-facing sprite. The clock overlay, the production tab icons,
  the cursors and the support power icons are drawn by the scripts, not TGMC art.
- The AI (`rules/ai.yaml`) trains units, sends them out in squads, and builds generators, tech and turrets with OpenRA's base-builder
  module (never walls). It has no builder to walk, so for the bot only, its cryo pod or silo counts as the build area.
  Pick "Skirmish AI (Easy)", "Skirmish AI" (Normal) or "Skirmish AI (Hard)" for a slot in the lobby. The three differ in squad size (a squad is
  `SquadSize` plus a random 0 to `SquadSizeRandomBonus` - 1 units) and attack timing: `scenario-ai-easy`, `-normal` and `-hard` measure when the first
  xeno reaches a marine 33 cells away (about 7000, 2200 and 1700 ticks). The xeno bot fires the Queen's Screech at three or more bunched marines. Bots use
  no deploy abilities (Pounce, Stealth) and no Orbital Strike or Flare: the engine's bot has no hook for them.
- The building system (Build tab, builder-range placement, tech gating, generators, walls) was checked headless: lint and
  `--check-yaml` pass; `scenario-build` checks that the tech buildings unlock only once built and that a Miner and a Weed Node add income;
  on Landing Zone (marine seat, driven with synthetic mouse clicks) the Build tab lists the structures with locked ones dimmed, a Miner and a Cade
  built and placed next to the Engineer, and a placement 10 cells from every builder was refused. In AI-vs-AI both bots build generators,
  tech and turrets (4 to 8 structures for the marines, 5 to 10 for the xenos by minute five); the marines still win (2 of 2 finished runs),
  so the xenos need more help. Not yet seen in play: the xeno Build tab (Drone and Queen ranges), dragging a wall line, and any tuning of
  the new income numbers (Miner +8 and Weed Node +7 every 2 s, base trickle 6, mini silo 3).
- The path menu -> Singleplayer -> Skirmish -> lobby (add a Skirmish AI, Start Game) was walked headless and works.
  `tgmc/chrome/mainmenu.yaml` is OpenRA's main menu in TGUI-style windows, without the news feed, update notice and player profile; `ingame-menu.yaml` does the same for the Esc menu.
- Verified by running the mod headless (OpenRA bleed, `mod/check_mod.sh` and `mod/smoke.sh`): the lint passes with
  no errors or warnings, and on Landing Zone the camera starts on the base, the radar and production palette work,
  the vendor spawns queued marines, income ticks up, and a "Skirmish AI" in the xeno slot trains Runners that attack
  the marine base. `mod/test_scenarios.sh` checks heal, repair, mend, victory, combat, every effect-carrying weapon (`scenario-fx`), the wave script and the AI. The xeno seat was played on Landing Zone against a marine bot: silo, mini silos, all four castes, palette and tooltips work.
  Not yet checked: voices (no audio device).
- AI against AI (`mod/balance.sh`, Landing Zone layout, fastest speed, the Normal bot on both sides), measured after veterancy, abilities, the
  Crusher, Boiler, mech and mortar, and research were added: the marines won 3 of 4 (at about 8000, 8500 and 10500 ticks) and the fourth was
  still undecided at the time limit, the xenos trading waves of 2 to 17 units against marine structures at 20 to 40% health. Earlier, before
  those additions, the marines won almost every match in 2 to 5 minutes of game time without the xenos reaching a structure, so the xenos are
  closer than they were, but the marines still have the better of it. On LV-624 the marines won 2 of 3 (at about 12000 ticks) and one was undecided.
  A human xeno player who attacks from several sides at once should do better than the AI.
- Hold the Line against a marine bot that holds the base (`mod/balance.sh 4 420 balance-holdline`): the marines win all
  four runs, finishing the last wave (16 Runners, 10 Hunters, 8 Sentinels) with about 30 units and 2 or 3 of their 5
  buildings. The waves attack-move to the marine base because `Hunt()` cannot see across the map for a scripted player.
- Tuning so far: the marine queue takes cost x 60% x 350% ticks (a rifleman is about 8 s) and the xeno queue x 250% (a Runner is about 3 s). Marines have
  120 HP and rifles do 14 every 15 ticks at 6 cells; Runners have 100 HP, run at speed 115 and claws do 20 every 14 ticks;
  Hunters 130 HP; sentries do 10; the corpsman heals 20 every 60 ticks.
  Base income is 6 cash every 2 s from the vendor and silo and 3 from a mini silo (it was 15 and 5 before the Build tab); a Miner gives 8 and a Weed Node 7.
  None of this has had real play time.
- `mod/setup.sh` was run from an empty directory on a fresh clone (it installed .NET, built OpenRA, made the sparse TGMC clone, built
  and linted the mod in about two minutes on a fast connection); a second run skipped the finished steps, and the scenarios, the smoke test
  and `play.sh hold-the-line` all ran afterwards. Only Linux x64 has been tried. macOS and WSL are untested.
- Fog of war is drawn with plain black quadrant tiles, so edges look blocky.
- The in-game MENU button now opens the Esc menu (the sidebar carries `MenuButtonsChromeLogic`). Checked headless: the menu, its objectives
  panel and Settings open with no missing sprites. The Smartgunner, Grenadier, Warrior, Crusher, Boiler, mech and mortar crew are new and have had the scenario tests but no play time.
- Not done, from the roadmap: a marine flamethrower to burn weeds, the Spitter and a marine Scout (the TGMC art for the Spitter is in the checkout),
  true spreading creep (it needs a small C# assembly), a lingering acid pool under the Boiler's bombs, and bots that use the Orbital Strike, Flare and the
  deploy abilities. Veterancy gives corpsmen and engineers nothing for healing and repairing: the engine has no hook for it.

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
