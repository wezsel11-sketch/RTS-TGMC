# Marine start: the Alamo lands and the marines walk out

Written 2026-11-15. Not started. Builds on `2026-10-17-alamo-starter-base.md` (the Alamo as the marines' landed base).

## Goal

A marine match opens as a TGMC round does: the Alamo comes down on the landing zone, the doors open, the squad walks
out of the hatch and forms up, and control passes to the player. About eight seconds, skippable, and the same for a
bot or a second human so the match stays fair and in sync.

## What exists

- `alamo` (`tgmc/rules/mapobjects.yaml:87`): the landed dropship, with door overlays driven by the conditions
  `doors-opening`, `doors-open`, `doors-closing` and `launch`.
- `Dropship` (`tgmc/code/Dropship.cs`): draws the hull coming down from `Height` over `LandTicks` with a growing
  shadow, and climbing away over `LaunchTicks`. A dropship that exists at world tick 0 skips the descent
  (`landing = self.World.WorldTick == 0 ? info.LandTicks : 0`, line 46). The fly-in is used by the evac mission only.
- `FactionStart` (`tgmc/code/FactionStart.cs`): at world load every player gets its faction's starting actors around
  its spawn, as `actor|dx|dy|facing`. The marines' squad appears standing beside the Alamo.
- Scenarios `evac-board`, `evac-early`, `evac-empty` cover the fly-in and the doors.

## Design

1. **Descent at match start.** `Dropship` gets `LandAtStart: true` for the start Alamo: it runs the descent from
   tick 0 instead of skipping it. The evac Alamo keeps today's behaviour.
2. **Squad rides inside.** `FactionStart` entries may carry a fourth field, `aboard`: those actors are not placed on
   the ground. They are created when the Alamo's `LandedCondition` comes on, at the hatch cell, one every few ticks,
   and each walks to its `dx|dy` cell. Structures in the list (if any) appear as now.
3. **Doors.** On landing: `doors-opening`, then `doors-open` while the squad leaves, then the doors stay open
   (the Alamo is the base; they close only for evac).
4. **Camera and control.** The local marine player's camera starts on the landing zone. Orders to the squad are
   possible as soon as each marine is on the ground; nothing is locked, so there is no "cutscene mode" to desync.
   The Alamo's build area turns on with the landed condition.
5. **Sound and effects.** Engine sound on approach, landing dust (roadmap C10), a thump and a short screen shake on
   touchdown, the door hiss, and one line in the alert feed: "Alamo is groundside". TGMC has the shuttle sounds
   (`sound/effects/` engine and landing clips; check names against `sound/credits.md` before use).
6. **Skip.** A lobby option "Landing intro" (default on). Off: today's start. Tests and the balance runner turn it
   off so their timings stay as they are.
7. **Xenos and SOM.** Out of scope here. Listed as follow-ups: the hive's larvae burrow up from the silo; SOM
   arrives by its own transport.

## Fairness and sync

- The descent lasts `LandTicks` (75, three seconds) plus unloading (about 100 ticks). A xeno player starts acting at
  tick 0, so the marines lose about seven seconds. Either the xeno start gets a matching delay (larvae hatch at
  tick 175), or the marine squad is ready at tick 0 and only the walk-out is shown. Decide by a balance run with the
  intro on and off; target no change in win rate beyond the run's noise.
- Everything is simulation state driven by world ticks. No `LocalRandom`, no local-player branches except the camera.

## Steps

1. `Dropship`: `LandAtStart`. Scenario: an Alamo at tick 0 is not landed until tick 75, then is.
2. `FactionStart`: `aboard` entries, spawned from the hatch on the landed condition. Scenario: at tick 60 no
   marine is on the map; by tick 250 all are, each at its cell.
3. Doors, build area and reveal gated on landing. Scenario: nothing can be placed before touchdown.
4. Lobby option and the test default (off for `scenario-*`, `balance-*`, `aimap-*` unless a test asks for it).
5. Sound, dust, shake, alert line. Filmstrip shot of the landing at ticks 10, 40, 75, 120, 200.
6. Balance run, intro on against off, 40 matches on three maps. Fix the timing if the marine win rate moves.
7. Full suite, lint, README section, release.

## Files

`tgmc/code/Dropship.cs`, `tgmc/code/FactionStart.cs`, `tgmc/rules/mapobjects.yaml` (alamo), `tgmc/rules/world.yaml`
(lobby option), the `FactionStart` lists in `mod/make_placeholders.py`, `mod/build_sounds.py`, new scenarios in
`mod/scenarios/`.

## Open questions for the user

- Should the player be able to give orders during the walk-out, or watch it?
- Should four-base maps land one Alamo per marine player (yes by default), and the second marine faction, SOM, too?
- Later: marines choosing the landing zone before the drop, as TGMC's pilot does.
