# Fable week roadmap (2026-11-11 to 2026-11-15)

This is a roadmap, not a task-by-task plan. Each track gets its own spec and plan in `docs/superpowers/` on the day it starts,
in the same form as `2026-11-07-reactive-ai.md`.

**Goal:** Use the week of Fable 5.2 access on the jobs that are large, cross-cutting and need one consistent eye: the HUD,
the look of the ground and the units, the effects, and the gameplay numbers.

**Two sessions run side by side.** Session 1 owns the HUD all week. Session 2 takes the other tracks in the order below.

## What the survey found (2026-11-11)

Read from the repo, `build/shots/*.png`, `build/balance-*.txt` and `docs/hud-designs/`.

HUD and UI
- The spec `2026-10-18-command-layer-and-hud-design.md` chose the floating layout, design C. The built HUD
  (`build/shots/shot-hud.png`) is still a right sidebar with flat blue buttons, and looks like none of the three mockups.
- The xeno seat shows "TGMC // COMMAND, MARINES VS XENOS", the word REQUISITION and the marine colours (`shot-xenohud.png`).
  There is no hive identity.
- Command buttons are text only, with no hotkey letter and no icon. Palette cells show no cost, name or hotkey.
- Support powers stack as up to ten small timers in the top-left corner; five of them read "ORBIT" with the same icon (`shot-groundfx.png`).
- The minimap frame is an empty grey box when there is no radar. The alert feed is one line.
- The palette is half empty on most tabs, and the sidebar takes the full height anyway.
- README "Known gaps": the selection card, ghost snapping, repeat build and lobby options have never been used with a mouse.

Graphics
- The grass tile is high-contrast noise. At game zoom it shimmers and the 32 px units are hard to see on it.
- No edge or transition tiles: shorelines, roads and rock are hard squares (README "Known gaps").
- Units are coloured by team, not by player. Two players on a side look the same.
- Runners have no attack frames. Marines have no lying-down body. A gib leaves no corpse.
- The shroud edge is a soft half-tile blend, but explored-and-dark ground and never-seen ground are both near black.

Effects
- Effects "have not been tuned by eye in a long match" (README). Every check so far is a single still frame.
- Lights exist (`tgmc/code/Lights.cs`, `shot-lighting.png`) but muzzle flashes, tracers and most explosions cast none.
- No screen shake, no impact decals that stay, no smoke that lingers. `shot-rain` exists but weather is not in any map's rules.

Gameplay
- The kits were ported from TGMC in four fast commits (`71b6981`, `419009d`, `4a332b6`, `c590afa`). Nobody has checked
  each number against the DM source.
- AI-vs-AI marine win rate in the saved runs ranges from 14% to 66%. The runs are from different code versions, so there is
  no current baseline, and every run is on one map (`balance-aivai`) though 37 `aimap-*` maps exist.
- `PLAN-upgrades.md`: the tab, two rifle upgrades and four xeno upgrades are built. Eight weapon families, armour, veterancy
  and research time are still plan.
- The SOM faction shares the marine ladder and has no identity of its own.
- The reactive-AI spec has a Part B (mission xenos, evac mission) with no plan file.

Foundations
- `tgmc/code` is 11,750 lines of C# with no `[Sync]` field at all, so a multiplayer desync would not be detected or located.
  13 uses of `world.LocalRandom` need a check that each one is cosmetic only (`Blood.cs:62` sits in a damage handler).
- `tgmc/code/Bots.cs` is 1,632 lines in one file.
- `tgmc/code/PerfProbe.cs` exists, but there is no saved measurement of a large battle since the twelve new castes.
- README "Known gaps" describes four castes and an older HUD. It is out of date.

## Track A: HUD and UI rebuild (Session 1, all week)

Owns: `tgmc/chrome/*.yaml`, `tgmc/code/Hud.cs`, `tgmc/code/Codex.cs`, `mod/make_chrome.py`, `tgmc/fluent/`, the
`shot-hud`, `shot-card*`, `shot-xenohud`, `shot-codex`, `shot-upgrades` scenarios. Nothing else.

1. **Layout.** Rebuild the in-game HUD to design C (`docs/hud-designs/c.html`, `design-c.png`): top-centre resource pill,
   left alert stack, round minimap top-right, selection card bottom-left, one hotkey bar bottom-centre, support powers bottom-right.
2. **Chrome atlas.** Rewrite the atlas in `mod/make_chrome.py`: rounded dark panels, amber accent, 1 px inner highlight,
   hover, pressed and disabled states for every button. No TGMC art.
3. **Hotkey bar.** Each cell shows hotkey letter, icon, name and cost. Locked cells show what unlocks them. Queue count and
   build progress draw on the cell.
4. **Command card.** Icon and hotkey on every order and ability. Cooldown as a radial sweep. Autocast as a corner mark.
5. **Faction skins.** Marine: olive, slate, amber. Xeno: resin purple and bone, "HIVE" title, plasma and biomass wording,
   organic panel edge. SOM: black and red. One atlas per faction, chosen by `faction-*` at world load.
6. **Support powers.** One tile per power type with a count badge, in place of ten timers. Ready state pulses.
7. **Alerts and pings.** A five-line feed with colour by kind. Clicking a line moves the camera. Minimap ping on each alert.
8. **Tooltips.** Unit and structure tooltips with cost, time, health, damage, range and a one-line role, read from the rules.
9. **Selection card.** Single unit: portrait, health, plasma, rank, kit, kills. Group: counts by type; click a type to narrow.
10. **Menus.** Main menu, lobby and Esc menu in the same atlas (mockup m3 in `docs/menu-designs/`).
11. **Scaling.** Every panel anchored, not absolute. Shots at 1280x720, 1920x1080 and 2560x1440 for both factions.

Proof for every step: a `mod/shots.sh` screenshot at three sizes, read by the session, plus the existing card and HUD scenarios passing.
Mouse-driven checks use the synthetic clicks that the Landing Zone build test already uses.

## Track B: Graphics (Session 2)

Owns: `mod/build_tileset.py`, `mod/build_sprites.py`, `mod/build_maptiles.py`, `mod/tgmc_turfs.py`, `tgmc/tilesets/`, `tgmc/sequences/`.

1. **Ground.** Lower the contrast of the ground tiles and add three or four variants each, so the ground reads as ground and units stand out.
2. **Transitions.** Edge and corner tiles for grass to dirt, grass to water, and floor to rock, built from TGMC's smoothing
   sheets. `mod/tgmc_dmm.py` picks the edge tile from the eight neighbours.
3. **Player colour.** Split each sprite into a base layer and a cloth or carapace mask at build time, and tint the mask with the
   player colour at draw time. This closes the "two players on one side share a colour" gap.
4. **Missing frames.** Runner attack frames, a marine lying-down body, and a corpse left behind after a gib.
5. **Shroud.** Explored-but-dark ground is dimmed and desaturated, not near black.
6. **Unit shadows and selection.** A soft ground shadow under every unit. Thinner selection ring with a health arc.

Proof: before and after screenshots of the same map and seed, at game zoom.

## Track C: Effects (Session 2)

Owns: `tgmc/code/Lights.cs`, `GroundFx.cs`, `ExplosionParticles.cs`, `Flames.cs`, `Shells.cs`, `Casings.cs`, `Blood.cs`,
`Gibs.cs`, `Corpses.cs`, `mod/test_effects.py`, the `shot-*` effect scenarios.

1. **Filmstrip tool first.** Extend `mod/shots.sh` to take N frames at fixed ticks and join them into one strip. All later
   steps are judged on strips, since a still cannot show timing.
2. **Light from fire.** Muzzle flash, tracer, explosion, flame and acid each cast a short light through `Lights.cs`.
3. **Impact.** Screen shake scaled by blast size and distance. Scorch, acid and blood decals that stay and fade over a minute.
4. **Smoke and dust.** Lingering smoke after explosions, dust from vehicles and landings, embers from fires.
5. **Weapon identity.** One pass per weapon family so rifle, SMG, shotgun, sniper, minigun, flamer, laser and plasma each
   look different in tracer, flash, sound and impact.
6. **Xeno abilities.** Each caste ability gets a wind-up telegraph and an impact effect, so a player can read and dodge it.
7. **Weather and night.** Rain, snow and ash as per-map rules. Night maps where lights and flares matter.

Proof: a filmstrip per effect, and `PerfProbe` showing a 200-unit fight still holds the frame budget.

## Track D: Gameplay (Session 2)

1. **Fidelity audit.** For every caste, weapon, vehicle and ability, read the DM source under `build/terragov-marine-corps`
   and compare with `tgmc/rules/*.yaml` and `tgmc/code/CasteAbilities.cs`. Output one table: TGMC value, mod value, verdict
   (match, scaled on purpose, wrong). Fix the wrong ones. Add a scenario test for each fixed ability.
2. **Balance baseline.** Run `mod/balance.sh` on the current commit across at least six `aimap-*` maps, 40 matches each, and
   save it as the baseline. All later balance claims are measured against it.
3. **Upgrades tab.** Finish `PLAN-upgrades.md`: the weapon ladders, armour, then veterancy (`GainsExperience`), research time,
   and economy upgrades. Each upgrade gets a with-and-without arm in `mod/balance.sh`.
4. **SOM identity.** The V-series ladder, black armour and one or two units of its own.
5. **AI.** Split `Bots.cs` by module. Add a build-order and counter-pick layer above the reactive modules. Xeno AI opens with
   a multi-direction attack. Target: marine win rate between 40% and 60% on the baseline maps.
6. **Missions.** Plan and build reactive-AI Part B. Turn the four `mission-*` scripts into a short campaign with a briefing each.

## Track E: Foundations (Session 2)

1. **Determinism audit.** Check all 13 `LocalRandom` uses and every `Dictionary` or `HashSet` iteration that feeds the
   simulation. Add `[Sync]` to the state that matters. Proof: two headless clients in one match with no desync for 20,000 ticks.
2. **Performance.** A 300-unit scenario with `PerfProbe`, saved as a number. Fix the top three hot traits.
3. **README.** Rewrite "Known gaps" from the current state.

## Second survey (2026-11-11, later): more to improve

Read from `shot-castes`, `shot-vehicles`, `shot-codex`, `shot-evac`, `shot-upgrades`, a converted map preview and the menu mockups.

Added to Track A (HUD and UI)
- A12. **Support power overflow.** With every power unlocked, 19 timers run down the left edge and over the minimap
  (`shot-upgrades.png`). Step A6 fixes the count; add a scroll or a second row for the rest.
- A13. **Palette overflow and icons.** The infantry tab holds 21 units. The last cell lands on the hint text
  (`shot-vehicles.png`). Most marine icons are the same dark-blue figure, so units cannot be told apart. Give each icon its
  weapon silhouette and a role glyph (heal, build, heavy, sniper), and group the tab into rows by role.
- A14. **Mission text.** On Evac the countdown "Alamo leaves in…" sits under the resource bar, the Command lines sit on the
  selection panel, and an "Unrevealed Terrain" tooltip covers the alert bar (`shot-evac.png`). Give objectives and
  countdowns their own panel, and keep chat lines clear of every panel.
- A15. **Codex.** It is one flat list with an "M" in front of each row; units, upgrades and armour are mixed
  (`shot-codex.png`). Rebuild it: faction tabs, groups (infantry, vehicles, structures, upgrades, powers), search, a large
  animated portrait, stat bars, a "strong against, weak against" line, and the evolution tree for xeno castes.
- A16. **Menu.** `docs/menu-designs/m3-menu.png` (green terminal, TACNET) has the strongest identity. Confirmed.
  Add a map picker with the real map preview, size, player count and a short description.
- A17. **End screen.** A debrief after each match: kills, losses, income and army size over time as graphs, and awards.
- A18. **Settings for the mod.** Hotkey profile (grid or classic), UI scale, colour-blind team colours, health bars always on.

Added to Track B (Graphics)
- B7. **Field maps.** The converted station maps are rich (`build/dev-maps/aimap-deltastation-full/map.png`), but the eight
  hand-made maps are flat grass with a square pond and a straight dirt strip (`shot-evac.png`). Redo them with cliffs, cover,
  props, tree lines and choke points, using the same converted tiles.
- B8. **Structures.** A marine building is one small machine sprite (vendor, locker, pod) on a single cell. Give each a
  footprint, a base plate, a build-up animation, a damaged state and a rubble state.
- B9. **Scale pass.** The tanks are 4 to 5 cells long, the APC between them is about one cell, and infantry are half a cell
  (`shot-vehicles.png`). Set one scale rule and apply it to every sprite.
- B10. **Idle life.** Units stand frozen. Add idle breathing or look-around frames where TGMC has them, and turret tracking.

Added to Track C (Effects)
- C8. **Sound pass.** `weapons.yaml` and `kit-weapons.yaml` have 33 `Report:` lines for 159 weapons, and the README says no
  sound has ever been heard. Check coverage with `tgmc/code/CheckSounds.cs`, level every sound to one loudness, add
  distance falloff and a limit on how many of one sound play at once.
- C9. **Death variety.** Per damage type: burnt by flame, melted by acid, gibbed by explosive, slumped by bullets.
- C10. **Dropship and pods.** The Alamo fly-in exists. Add engine glow, landing dust, a shadow that grows on approach, and
  the same treatment for drop pods and the Condor strike run.

Added to Track D (Gameplay)
- D7. **Test suite health.** The last full run (2026-10-31) was 120 of 121; `scenario-ai-marine-fields-easy` prints PASS on a
  line marked FAIL. About 17 tests are newer than that run. Run the whole suite on the current commit first, and fix it.
- D8. **Cover and terrain.** Cades and walls exist. Add cover from props and cliffs (less damage taken from the far side)
  and high ground (more range), so the redone maps in B7 change how fights go.
- D9. **Control feel.** Formation move, attack-move spread, smart-cast abilities on a mixed group, control groups shown on
  the HUD, rally points, and a "select all army" key. None has been used with a mouse yet.
- D10. **Game modes.** TGMC's own modes map well to an RTS: Distress (base against hive), Crash (escape with the Alamo, the
  evac mission is the start of it), and a co-op wave mode for two marine players.
- D11. **Onboarding.** A ten-minute tutorial mission per faction, and hints that fire the first time a player meets a mechanic.

Found on 2026-11-11 (D7)
- `scenario-ai-defend` fails about one run in four, on the build before today's changes too (2 of 10): no rifleman goes to help
  the miner. `scenario-ai-easy` fails about one run in five: the Easy xeno bot ends tick 1000 with one or two units.
  Both are the bots' behaviour under some seeds, not the tests. They belong to D5.
- The Fatty's ring of eight and every rocket used the pyrogen's blue fire as their blast. Fixed.

Balance baseline (D2), commit `e583359`, 2026-11-11
`mod/balance.sh 40 400 <map>`, Skirmish AI on both sides, 40 matches a map. Marine win rate is of the matches that ended.

| Map | Marines | Xenos | No result | Marine win rate (95%) | Median end tick |
|---|---|---|---|---|---|
| balance-aivai | 21 | 12 | 7 | 64% (47% to 78%) | 12000 |
| aimap-canyon-run | 32 | 8 | 0 | 80% (65% to 90%) | 14000 |
| aimap-jungle-crossing | 30 | 10 | 0 | 75% (60% to 86%) | 14000 |
| aimap-close-quarters | 26 | 14 | 0 | 65% (50% to 78%) | 13000 |
| aimap-twin-rivers | 36 | 4 | 0 | 90% (77% to 96%) | 17000 |
| aimap-quarry-pit | 32 | 6 | 2 | 84% (70% to 93%) | 19000 |
| All six | 177 | 54 | 9 | 77% | |

The marines are ahead on every map, and furthest ahead on the two where matches run longest. The target is 40% to 60%.

Decided
- HUD: design C, confirmed by the user on 2026-11-11.
- Menus: mockup m3 (green TACNET terminal), confirmed 2026-11-11.
- Per-player colour (B3): yes, confirmed 2026-11-11.
- Multiplayer is not needed. E1 determinism audit is out of the week.

## Order for Session 2

| Day | Work |
|-----|------|
| Wed 11 | D7 full test suite, D2 balance baseline (runs in background), C1 filmstrip tool |
| Thu 12 | D1 fidelity audit and fixes |
| Fri 13 | B1 to B3 ground, transitions, player colour |
| Sat 14 | C2 to C6 effects pass; B4 to B6 |
| Sun 15 | D3 upgrades tab; D5 AI balance against the baseline; E3 README |

Left for after the week: E1 determinism audit (multiplayer not needed). If time runs out, also: D4 SOM identity, D6 missions, C7 weather and night, E2 performance.

## Running two sessions

- File ownership is the split. Session 1 touches only the Track A files. Session 2 touches everything else.
- Both sessions write to `build/`. Session 1 uses its own copy of the build tree, the way the `balance-base` run used a
  scratchpad copy, so a rebuild in one session does not break a test run in the other.
- Small commits, rebased often. `tgmc/fluent/` is the one place both will edit; keep additions at the end of the file.

## Open decisions

None. All second-survey items are in scope (user, 2026-11-11). Order within each track: the first-survey steps, then the second-survey steps.
