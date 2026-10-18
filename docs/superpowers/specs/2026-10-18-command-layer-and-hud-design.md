# Command layer and HUD refresh: design

Date: 2026-10-18. Status: draft for review. Sub-project 1 of 4 in "closer to a modern RTS" (the others: production flow, selection, feedback and info; see Scope).

## Goal

Make TGMC's controls and in-game UI feel closer to a modern RTS, for all three factions (Marines, Xenos, SOM). This sub-project delivers player-facing stance control, a retreat order, queued abilities, alert feedback, and a new floating HUD.

## Success criteria

- A player can set Hold Fire, Return Fire, Defend or Attack Anything on any selected combat unit of any faction from the HUD and from hotkeys.
- A player can order selected units to retreat to the nearest friendly return point, for every faction.
- Holding Shift while using an ability hotkey (R, T) queues the ability behind the current orders.
- Under-attack and idle-production events show as toasts and minimap pings, without spamming.
- The in-game HUD uses the "floating minimal" layout (design C), and the Codex, Help and Stats panels still work.
- `mod/lint_static.py` reports 0 errors, `mod/check_mod.sh` passes, new scenario tests pass, and `mod/smoke.sh` reports no exception log.

## Scope

In scope: stance buttons and hotkeys; `TgmcRetreat`; queued abilities; shift-queue verification; `AlertFeed`; HUD chrome rewrite for the floating layout; optional panel fade.

Out of scope here (later sub-projects, each with its own spec): production flow (rally on every producer, per-unit production hotkeys, repeat-build), selection (subgroup cycling, select-army, group feedback), richer info (status bars, tooltips). Also out of scope: a new `StanceControl` trait, a C# test project, replays or observer additions, camera bookmarks, hotkey remapping UI.

## Findings that shape the design

- OpenRA at the pinned commit already has stances: `AutoTarget.SetStance`, the `SetUnitStance` order and `StanceSelectorLogic`. `EnableStances` is not disabled in the mod's rules. The mod's chrome has no stance widget, so the work is wiring a control, not new stance logic.
- Only 18 explicit `AutoTarget` entries appear across about 66 actors in `tgmc/rules/units.yaml`. Task 1 must verify that every combat unit inherits `AutoTarget`, and add it where missing.
- The mod already has the hotkeys `TgmcAbility1` (R), `TgmcAbility2` (T), `TgmcSelectIdle`, `TgmcSelectWounded`, `TgmcSelectAllOfType`, and C# in `tgmc/code` (about 7,400 lines, built to `Tgmc.dll`).
- The Codex, Help and Stats panels live in `tgmc/chrome/ingame-player.yaml` and must keep working.

## Design

### HUD layout (design C, floating minimal)

Minimap bottom-left. Selection panel bottom-centre (about 30% of width): portraits and health, stance row, retreat button, contextual command card. Production queue bottom-right. Resource strip (cash, income, army) top-right. Alert toasts top-left. Panels are small so the map shows through. Faction skins (marine, hive, SOM) are chosen by one `Background:` name per faction.

### Components

1. **Chrome YAML.** Rewrites the HUD panels in `tgmc/chrome/ingame-player.yaml` and `ingame.yaml`; reuses `tgui-window` backgrounds. Leaves the Codex, Help and Stats panels untouched.
2. **`CommandCard` widget logic (C#).** Reads the selection and draws contextual buttons: stance, retreat, abilities, and queued-ability markers while Shift is held. Follows OpenRA's logic-class pattern.
3. **`TgmcRetreat` order and `RetreatOrder` trait (C#).** Moves units to the nearest friendly return point. A per-faction `ReturnPoint` marker trait in YAML names qualifying structures (supply or landing structures for Marines and SOM, hive structures for Xenos). If no return point exists, the order is rejected and units keep their current orders.
4. **Queued abilities (C#).** Extends the ability-issuing code in `Abilities.cs` and `CasteAbilities.cs` so a Shift-held ability hotkey queues the use behind current orders. The exact shape depends on how those abilities are issued today and is confirmed in the plan's first read-through.
5. **`AlertFeed` (C#).** Collects under-attack and idle-production events, draws toasts and minimap pings, and rate-limits repeats.
6. **Panel fade (C#, optional).** Dims panels when nothing is selected and nothing is happening. First thing cut if scope grows.

### Data flow

Click or hotkey, then widget logic issues an order, then the trait resolves it, then the unit acts. Events flow back to `AlertFeed`. All orders use the engine's normal order pipeline, so multiplayer sync and replays keep working.

### Error handling

Retreat with no return point is rejected, not crashed. A stance change on a mixed-faction selection applies to every selected unit that supports stances. A killed unit's toast is dropped safely. Shift-queue with an ability on cooldown skips the ability and continues the queue.

## Testing

Existing harness is extended, not replaced.

1. `mod/lint_static.py`: 0 errors after every task.
2. `mod/check_mod.sh`: OpenRA YAML lint passes.
3. New scenario maps run by `mod/test_scenarios.sh` (each prints `TEST <name> PASS`): `test-stance-*` (Hold Fire does not shoot, Attack Anything does; one unit each from Marines, Xenos, SOM), `test-retreat` (all three factions, plus the no-return-point case), `test-queued-ability`, `test-shift-queue`, `test-alert-feed` (one alert, no spam).
4. `mod/smoke.sh`: launch, screenshot, no exception log. Screenshots are checked at 1280x720 and at a smaller size. Scenarios can run with `SDL_VIDEODRIVER=offscreen`.
5. Human check: HUD readability and fade feel, from screenshots.

Edge cases covered: retreat with no return structure; stance on a mixed Marine and Xeno selection; Shift-queue with a cooldown ability; unit killed while its toast shows; Codex, Help and Stats panels open after the rewrite.

Limits: scenario tests run in real time at 25 ticks a second, up to 150 seconds each. There is no C# unit-test project and none is added here.

## Risks

- The chrome rewrite is the largest change and can break existing panels. Mitigation: touch only the HUD panels, run `smoke.sh` after each chrome task.
- Mockups for design C are untested at small window sizes.
- The OpenRA commit is pinned, so widget APIs are fixed, but anything this design assumes about them must be confirmed against `build/OpenRA` in the plan.

## Constraints

- Non-commercial use only; never commit `build/` or any TGMC-derived art.
- OpenRA and TGMC stay pinned to the commits in `mod/bootstrap.py`.
- Nothing is committed beyond this spec until the user approves.
