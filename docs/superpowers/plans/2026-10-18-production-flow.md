# Production flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rally points on every unit producer with a visible rally line, per-unit production hotkeys, and a repeat-build toggle for each queue.

**Architecture:** Mostly YAML: add `RallyPoint` to producers, key bindings on palette buttons, a `RepeatBuild` trait on queues. C# adds a `RallyLine` renderer trait and the repeat logic. Tests are Lua scenario maps.

**Tech Stack:** OpenRA YAML (rules, chrome, hotkeys), C# (`tgmc/code`), Lua scenarios (`mod/scenarios/`), `mod/make_placeholders.py`, `mod/lint_static.py`, `mod/check_mod.sh`.

**Spec:** `docs/superpowers/specs/2026-10-18-production-flow-design.md` (approved, committed `3897f85`). The spec is the binding authority.

## Global Constraints

- Non-commercial use only; never commit `build/` or any TGMC-derived art.
- OpenRA and TGMC stay pinned to the commits in `mod/bootstrap.py`.
- No change to unit costs or build times.
- Stance hotkeys and existing `TgmcAbility*` keys are not rebound.
- Repeat default: off. Repeat hotkey: `Y` (confirm unbound in `tgmc/hotkeys.yaml` and OpenRA `mods/common/hotkeys/game.yaml` in Task 3).

## Review Focus

1. Repeat-build with the producer destroyed mid-queue: no exception, queue lost, no refund.
2. Repeat-build with enough cash for one unit but not two: the second waits, is not charged early.
3. Rally point set to an unreachable cell: unit walks to the nearest reachable cell.
4. Production hotkey pressed while the item is not buildable (tech missing or not enough cash): no order issued, no error.
5. Rally line drawn for a producer that is not selected: must not appear.

Each line is pinned by a test in the task that owns the code.

---

## Pre-flight

| Producer | Consumer | Found | Ruling |
|---|---|---|---|
| Task 1 rally audit | Task 2 rally line | Six structures already have `RallyPoint` (`resin-silo`, `mini-silo`, `forward-hive`, `vendor`, `cryo-pod`, `workshop`). `engineer`, `drone` and `queen` have `Production` with no `RallyPoint`. | Task 1 decides per unit below. |
| Task 3 palette keys | Task 4 repeat | Both touch `ProductionPalette` / `ProductionBar`. | Repeat button goes on `ProductionBar`; hotkey keys do not overlap. No conflict. |
| `MultiProductionQueue.QueueUnit` | Task 3 hotkeys | Existing script property queues one unit. | Hotkeys reuse it. |

Ruling on the three non-rally producers: `engineer` is a builder and builds structures, not units, so it gets no rally point and no repeat. `drone` and `queen` are Xeno producers; `queen` gets a `RallyPoint` if it spawns units from its own production bar, otherwise it is excluded. Task 1 confirms by reading each one's `Production:` block. Cost if wrong: one YAML line.

---

## Task 1: Rally audit and points

**Files:**
- Modify: `tgmc/rules/units.yaml` (`drone`, `queen` if they spawn units)
- Test: none (YAML audit + lint)

**Interfaces:**
- Consumes: `RallyPoint` (stock trait).
- Produces: every unit producer carries `RallyPoint`.

- [ ] **Step 1: Read the three `Production:` blocks** in `units.yaml` (`engineer`, `drone`, `queen`). Decide per the Pre-flight ruling. Record each decision in `progress.md` as a Ruling.
- [ ] **Step 2: Add `RallyPoint:`** to any that spawn units, copying the block shape used in `structures.yaml` (`RallyPoint:` with a `Path:` of two cells offset from the producer).
- [ ] **Step 3: Lint.** `python3 mod/lint_static.py` (0 errors).
- [ ] **Step 4: Commit.**
```bash
git add tgmc/rules/units.yaml
git commit -m "Rally points on Xeno unit producers that spawn units"
```

---

## Task 2: Rally line and test

**Files:**
- Create: `tgmc/code/RallyLine.cs` (`RallyLineInfo`, `RallyLine`: line from producer to rally cell, drawn only while the producer is selected)
- Modify: `tgmc/rules/structures.yaml` and `units.yaml` (`RallyLine:` on each producer with `RallyPoint`)
- Create: `mod/scenarios/test-rally.lua`
- Modify: `mod/make_placeholders.py` (`scenario-rally`)

**Interfaces:**
- Consumes: `RallyPoint` (stock trait, `Path` cells), selection state of the producer.
- Produces: `RallyLine` trait; script property `RallyTo(cell)` for tests (sets the rally point).

- [ ] **Step 1: Failing test.** `test-rally.lua`: a Marines producer (`cryo-pod`) with a rally point; script calls `RallyTo(CPos.New(16,10))`; after the producer builds one rifleman from its queue, assert the rifleman reaches within one cell of the rally point by tick 1500. Print `TEST rally PASS` or FAIL.
- [ ] **Step 2: Run, expect FAIL** (`RallyTo` missing).
- [ ] **Step 3: Implement** `RallyLine` (draw line from producer centre to rally cell only when the producer is selected). Add `RallyTo` on a script property group following the `ActiveAbilityProperties` pattern in `CasteAbilities.cs`.
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Review Focus items 3 and 5.** Add to `test-rally.lua`: rally to a wall cell; unit ends within reach of it, no exception. And a second producer not selected: no line drawn. Watch fail, then pass.
- [ ] **Step 6: Lint, check, commit.**

---

## Task 3: Per-unit production hotkeys

**Files:**
- Modify: `tgmc/hotkeys.yaml` (`ProductionInfantry1`…`ProductionInfantry6`, `ProductionXeno1`…`ProductionXeno6`, `ProductionBuild1`…`ProductionBuild6`)
- Modify: `tgmc/chrome/ingame-player.yaml` (palette buttons: `Key:` lines)
- Modify: `tgmc/fluent/tgmc.ftl` (`hotkey-description-…` for each new key)
- Create: `mod/scenarios/test-hotkey-queue.lua`
- Modify: `mod/make_placeholders.py` (`scenario-hotkey-queue`)

**Interfaces:**
- Consumes: `MultiProductionQueue.QueueUnit` (existing), `HotkeyPrefix: Production`.
- Produces: the key names above.

- [ ] **Step 1: Confirm key names are free** in `build/OpenRA/mods/common/hotkeys/game.yaml` and `tgmc/hotkeys.yaml`. Record in ledger.
- [ ] **Step 2: Failing test.** `test-hotkey-queue.lua`: call `QueueUnit` for slot 1 and assert the queue count goes 0→1; with insufficient cash, assert the count stays 0 (Review Focus item 4). Print PASS/FAIL.
- [ ] **Step 3: Run, expect FAIL.**
- [ ] **Step 4: Add `Key:` lines and hotkey entries.** Each palette button in `PRODUCTION_PALETTE` gets `Key: ProductionInfantry<n>` (and the Xeno and Build equivalents). Fluent description keys added.
- [ ] **Step 5: Run, expect PASS.**
- [ ] **Step 6: Lint, check, commit.**

---

## Task 4: Repeat-build

**Files:**
- Create: `tgmc/code/RepeatBuild.cs` (`RepeatBuildInfo`, `RepeatBuild`: per-queue flag; on head-item completion, re-queue it if the flag is on and it is affordable)
- Modify: `tgmc/rules/*.yaml` (`RepeatBuild:` on each producer with `Production:` that builds units)
- Modify: `tgmc/chrome/ingame-player.yaml` (`Button@REPEAT_BUILD` on `ProductionBar`; toggles the flag)
- Modify: `tgmc/hotkeys.yaml` (`TgmcRepeatBuild: Y`)
- Modify: `tgmc/fluent/tgmc.ftl` (`cmd-repeat`, `hotkey-description-tgmcrepeatbuild`)
- Create: `mod/scenarios/test-repeat.lua`, `mod/scenarios/test-repeat-broke.lua`
- Modify: `mod/make_placeholders.py` (`scenario-repeat`, `scenario-repeat-broke`)

**Interfaces:**
- Consumes: `ProductionQueue` head completion (engine), cash (`PlayerResources`).
- Produces: `RepeatBuild` trait; script properties `SetRepeat(bool)` and `RepeatOn` on the producer's queue.

- [ ] **Step 1: Failing tests.**
  - `test-repeat.lua`: enable repeat on a `cryo-pod`, give ample cash; after two build cycles, assert two riflemen produced. With repeat off, one.
  - `test-repeat-broke.lua`: repeat on, cash for one unit only; after the first finishes, assert the second waits and cash is not charged twice (Review Focus item 2).
  Print PASS/FAIL.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** `RepeatBuild`: subscribe to queue completion; if the flag is on and `QueueUnit` is affordable, queue again; otherwise do nothing (waits).
- [ ] **Step 4: Add the toggle button, hotkey and YAML.**
- [ ] **Step 5: Run, expect PASS** for both scenarios.
- [ ] **Step 6: Review Focus item 1.** Add to `test-repeat.lua`: destroy the producer mid-queue; assert no `LuaException` in the log and cash unchanged. Watch fail, then pass.
- [ ] **Step 7: Lint, check, commit.**

---

## Task 5: Full verification

- [ ] `python3 mod/lint_static.py` reports 0 errors.
- [ ] `mod/check_mod.sh` passes.
- [ ] Each new scenario prints PASS: `rally`, `hotkey-queue`, `repeat`, `repeat-broke`.
- [ ] Headless `ScreenshotAt` run (as in sub-project 1) shows the production bar with the repeat button and no exception log.
- [ ] Human check: rally line and repeat button on the HUD (spec testing item 4). Hand to the user.
