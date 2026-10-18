# Command layer and HUD refresh: design

Date: 2026-10-18. Status: amended 2026-10-18 after reading the existing HUD code (first draft assumed controls that already exist). Sub-project 1 of 4 in "closer to a modern RTS" (the others: production flow, selection, feedback and info; see Scope).

## Goal

Make TGMC's controls and in-game UI feel closer to a modern RTS, for all three factions (Marines, Xenos, SOM). This sub-project closes the real gaps in the command card (Attack Anything stance, a true Retreat order, Shift-queued abilities), adds an under-attack alert, and restyles the existing bottom console into the floating "design C" layout.

## What already exists (verified in code)

- `tgmc/chrome/ingame-player.yaml` has a full bottom `DOCK` (radar, `SELECTION_PANEL`, `GROUP_PANEL`, `COMMAND_CARD`), a left `BUILD_PANEL`, a centred `TOP_BAR`, a right-hand `EVENT_LOG` and a `SUPPORT_POWERS` palette. The Codex, Help and Stats panels live in the same file.
- `CommandCardLogic` (`tgmc/code/Events.cs`) already issues Stop, attack-move, Patrol, the Defend, Return Fire and Hold Fire stances (buttons Guard, Return, Hold), medic and infected buttons, and the two ability buttons (hotkeys `TgmcAbility1` R, `TgmcAbility2` T).
- Every combat unit inherits `AutoTarget` from `^Unit` (`InitialStance: AttackAnything`), so every faction supports all four stances. SOM units (`som_trooper`, `som_veteran`, `som_corpsman`) are ordinary actors with a `~faction-som` prerequisite.
- `TgmcEventLog` (event log entries and counts), `RadarPings`, and a base-attack notification already exist. No per-unit under-attack alert exists.
- The fluent key `cmd-aggressive` exists but no button uses it.

## Success criteria

- A player can set Hold Fire, Return Fire, Defend or Attack Anything on selected units from the command card, and the four stance keys (`StanceAttackAnything`, `StanceDefend`, `StanceReturnFire`, `StanceHoldFire`) work.
- A Retreat button and hotkey (`TgmcRetreat`, V) send selected units to the nearest friendly return point, for every faction; with no return point the order is refused and nothing changes.
- Holding Shift while pressing an ability button or hotkey queues the ability behind the current orders; an ability not ready when its turn comes is skipped and the queue continues.
- A unit hit by an enemy raises one "under attack" log entry and one minimap ping, at most once per 250 ticks per player.
- The in-game HUD uses the floating layout (design C) and the Codex, Help and Stats panels still open and close.
- `mod/lint_static.py` reports 0 errors, `mod/check_mod.sh` passes, the new scenario tests pass, and `mod/smoke.sh` reports no exception log.

## Scope

In scope: Attack Anything button and stance keys; `Retreat` (trait, `ReturnPoint` marker, order, button, hotkey); Shift-queued abilities; under-attack alert; restyle of the existing console to design C.

Deferred: idle-production alerts (no agreed definition of "idle"; revisit with the feedback sub-project), panel fade (OpenRA chrome widgets have no opacity control, so it needs a custom widget), faction-specific panel skins, production flow, selection work, status bars and tooltips, camera bookmarks, hotkey remapping UI, replay and observer additions, a C# test project.

## Design

### Command card (YAML and existing `CommandCardLogic`)

Add two buttons in a free third row of `COMMAND_CARD`: `CMD_AGGRESSIVE` (Attack Anything) at X 0, Y 108 and `CMD_RETREAT` at X 76, Y 108, both 72x30 like their neighbours. `CMD_AGGRESSIVE` joins the existing stance loop. The four stance buttons get `Key:` bindings to the stance hotkeys OpenRA already defines. `CMD_RETREAT` issues the `TgmcRetreat` order.

### Retreat (new C#, `tgmc/code/Retreat.cs`)

- `ReturnPoint` marker trait, placed on structures a faction retreats to: `cryo-pod` and `medbay` (Marines and SOM, who build the same structures), `resin-silo` and `forward-hive` (Xenos).
- `Retreat` trait on `^Unit`, resolving the `TgmcRetreat` order: pick the nearest live `ReturnPoint` owned by the unit's player, cancel the current activity (queue it behind current ones when Shift is held) and move there with a plain move that does not stop to fight. No return point: the order is ignored.
- A Lua script property `Retreat()` (returns whether an order was accepted) so scenario tests can drive it.

### Queued abilities (existing `ActiveAbility` in `CasteAbilities.cs`)

`ActiveAbility.ResolveOrder` currently calls `Use(self)` immediately and ignores `order.Queued`. When `Queued` is set it instead queues a small activity that calls `Use` when reached and finishes whether or not the use succeeded. The ability buttons read `Game.GetModifierKeys()` for Shift when building the order. Script properties `QueueAbility(slot)` and `AbilityReady(slot)` support the scenario test.

### Under-attack alert (new C#, `tgmc/code/Alerts.cs`)

An `AlertOnDamage` trait on `^Unit` implements `INotifyDamage`. For positive damage from an enemy attacker it calls `TgmcEventLog.PostLimited`, a new method that posts only if the player has not posted that key within a cooldown, and adds a `RadarPings` ping. A `ScriptPlayerProperties` `EventCount(key)` reads `TgmcEventLog.Count` for tests.

### HUD restyle (YAML only)

Edit positions, not widgets. `DOCK` becomes a transparent container; its children float as cards: radar bottom-left, `SELECTION_PANEL`, `GROUP_PANEL` and `COMMAND_CARD` (now a `tgui-card` background) grouped bottom-centre. `BUILD_PANEL` moves to the right edge. `TOP_BAR` moves top-right. `EVENT_LOG` moves top-left as the alert toasts, with the `SUPPORT_POWERS` palette shifted right to clear it. Codex, Help and Stats panels are not touched.

### Error handling

Retreat with no return point is refused (no crash, no state change). A stance or retreat order on a mixed selection applies to every selected unit that can use it. A queued ability not ready on its turn is skipped. Alert entries for dead units are harmless (the log stores a position, not an actor).

## Testing

1. `mod/lint_static.py`: 0 errors after every task (new Fluent keys, sequences).
2. `mod/check_mod.sh`: OpenRA YAML lint.
3. New scenario maps, registered in `SCENARIOS` in `mod/make_placeholders.py`, scripts in `mod/scenarios/`, run by `mod/test_scenarios.sh`, each printing `TEST <name> PASS`: `test-stance` (all four stances settable for a Marine, SOM and Xeno unit; Hold Fire does not shoot, Attack Anything does), `test-retreat` (all three factions reach their return point) and `test-retreat-none` (refused, no movement), `test-queued-ability`, `test-alert` (damage raises exactly one alert in the cooldown window).
4. `mod/smoke.sh` after each chrome task: launch, screenshot, no exception log. Screenshots checked at 1280x720 and a smaller size.
5. Human check of the finished HUD from screenshots.

Edge cases covered: retreat without a return point; queued ability while moving; ability on cooldown in a queue; repeated damage within the cooldown; Codex, Help and Stats panels after the restyle.

Limits: scenario tests run in real time (25 ticks a second, up to 150 s each). Button clicks and Shift detection run in widget code that scenarios cannot reach; those are covered by the smoke test, the lint, and the manual check. No C# unit-test project is added.

## Risks

- The restyle touches the most-used screen; any wrong coordinate shows up only in a screenshot. Mitigation: one chrome task per region, `smoke.sh` and a screenshot after each.
- The chrome expression syntax (arithmetic with `WINDOW_WIDTH`, parentheses) must be confirmed on the first edit.
- The pinned OpenRA commit means engine APIs are fixed; every API named in the plan was checked against `build/OpenRA`.

## Constraints

- Non-commercial use only; never commit `build/` or any TGMC-derived art.
- OpenRA and TGMC stay pinned to the commits in `mod/bootstrap.py`.
- Nothing is committed beyond this spec and plan until the user approves.
