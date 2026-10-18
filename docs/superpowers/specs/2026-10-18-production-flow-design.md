# Production flow: design

Date: 2026-10-18. Status: draft for review, not committed. Sub-project 2 of 4 in "closer to a modern RTS" (sub-project 1, command layer and HUD, is done; see `2026-10-18-command-layer-and-hud-design.md`).

## Goal

Make building units feel closer to a modern RTS, for all three factions (Marines, Xenos, SOM). The player sets a rally point on any producer, queues units by hotkey, and repeats a build without re-clicking.

## What already exists (verified in code)

- Producers in `tgmc/rules/structures.yaml` (`resin-silo`, `mini-silo`, `forward-hive`, `vendor`, `cryo-pod`, `workshop`, and others) carry `Production:` and `ProductionBar:`. Most already have `RallyPoint:`, but not all producers were checked.
- `MultiProductionQueue` (`tgmc/code/ProductionQueues.cs`) is a parallel classic queue with a script property `QueueUnit`.
- `ProductionPalette` with `HotkeyPrefix: Production` and `SelectProductionBuildingHotkey` is wired in `ingame-player.yaml` (`PRODUCTION_PALETTE`, around line 576).
- Rally points are set by the stock right-click order. There is no hotkey for it and no visible rally line for every producer.
- There is no repeat-build. A finished item is not re-queued.

## Success criteria

- Every producer that builds units has a `RallyPoint`, and the player can set it with the stock right-click order on the producer.
- A rally point is drawn as a line from the producer to its marker while the producer is selected.
- Per-unit production hotkeys: each palette button has a key, and pressing it queues one unit.
- Repeat-build: a `Repeat` button on the production bar (and a hotkey) re-queues the selected queue's head item each time it finishes, until toggled off.
- Works for Marines, Xenos and SOM; no change to unit costs or build times.
- `mod/lint_static.py` reports 0 errors, `mod/check_mod.sh` passes, new scenario tests pass.

## Scope

In scope: `RallyPoint` on every unit producer; rally line drawn while selected; per-unit production hotkeys on the palette; repeat-build toggle (button and hotkey) for each queue; scenario tests for each.

Out of scope: changing costs or build times; new production buildings; the HUD restyle (done in sub-project 1); selection work (sub-project 3); status bars and tooltips (sub-project 4); faction skins.

## Design

### Rally points

Add `RallyPoint:` to any producer without one, using the existing trait. The rally marker is the trait's own, so no new C# is needed for setting the point. The new work is the line: a small `RallyLine` renderer trait on the producer, drawn only while the producer is selected, from the producer's centre to the `RallyPoint` location, in the player's colour.

### Per-unit production hotkeys

`ProductionPalette` already has `HotkeyPrefix: Production`. Give each palette button a key from the `Production` prefix (for example `ProductionInfantry1` through `ProductionInfantry9`). Pressing one calls the existing queue-one path (`MultiProductionQueue.QueueUnit`, or the stock `StartProduction` order). No new order type.

### Repeat-build

A `RepeatBuild` trait on each queue's actor, with a per-queue boolean. When the head item completes and the flag is on, it re-queues the same item. The normal production cost is still paid. A button on `ProductionBar` toggles the flag; a hotkey (`TgmcRepeatBuild`, default `Y`) does the same for the selected queue. When the player is out of cash the queue waits, and nothing is refunded.

### Error handling

A rally point on an unreachable cell: the unit walks to the nearest reachable cell (the stock behaviour). Repeat with no cash: the queue waits. A producer destroyed mid-queue: its queue is lost, as the engine already does. Hotkey pressed on an unbuildable palette item: no order is issued.

## Testing

1. `mod/lint_static.py`: 0 errors after each task (new Fluent keys, hotkeys, sequences).
2. `mod/check_mod.sh`: OpenRA YAML lint passes.
3. Scenario maps, registered in `SCENARIOS` in `mod/make_placeholders.py`, scripts in `mod/scenarios/`:
   - `test-rally`: a Marines producer with a rally point; a unit built there walks to the rally point.
   - `test-hotkey-queue`: the production hotkey queues one unit (queue count goes from 0 to 1).
   - `test-repeat`: with repeat on and enough cash, two units are built back to back; with repeat off, one.
   - `test-repeat-broke`: with repeat on and no cash, the queue waits and nothing is spent.
4. `mod/smoke.sh` after each chrome change; screenshot check of the production bar.

Limits: scenarios run in real time. Button clicks and hotkey binding are widget code; they are covered by lint and the smoke screenshot.

## Risks

- Rally line rendering is new and visual; it could clutter the map. Mitigation: draw only for the selected producer, thin line, one colour.
- Repeat-build could drain cash in a loop. Mitigation: it only re-queues when the queue is empty and the item is affordable, and the toggle is off by default.
- Some producers may lack `RallyPoint`. The audit in task 1 lists them before any YAML is edited.

## Open questions (defaults chosen; say if you want otherwise)

- Repeat is off by default. Default key `Y`.
- Repeat waits on cash shortage; it does not cancel.
- Rally line is drawn only while the producer is selected.

## Constraints

- Non-commercial use only; never commit `build/` or any TGMC-derived art.
- OpenRA and TGMC stay pinned to the commits in `mod/bootstrap.py`.
- Nothing is committed until the user approves this spec.
