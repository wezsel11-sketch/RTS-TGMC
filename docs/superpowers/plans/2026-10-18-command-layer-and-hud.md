# Command layer and HUD refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the real gaps in TGMC's command card (Attack Anything stance, a true Retreat order, Shift-queued abilities), add an under-attack alert, and restyle the existing bottom console to the floating design C layout.

**Architecture:** The command card already exists in `CommandCardLogic` (`tgmc/code/Events.cs`) and in `tgmc/chrome/ingame-player.yaml`. New behaviour is C# traits on `^Unit` and structures, one new order (`TgmcRetreat`), a queue path inside `ActiveAbility.ResolveOrder`, and a rate-limited wrapper around the existing `TgmcEventLog`. The HUD restyle is YAML position and background changes only. Tests are Lua scenario maps run by `mod/test_scenarios.sh`.

**Tech Stack:** C# (OpenRA engine at the pinned commit in `build/OpenRA`, mod code in `tgmc/code`), OpenRA YAML (rules, chrome, hotkeys), Lua scenario scripts (`mod/scenarios/`), Python map generator (`mod/make_placeholders.py`), shell harness (`mod/test_scenarios.sh`, `mod/smoke.sh`, `mod/check_mod.sh`, `mod/lint_static.py`).

**Spec:** `docs/superpowers/specs/2026-10-18-command-layer-and-hud-design.md` (amended 2026-10-18, uncommitted at plan time). The spec is the binding authority; this plan argues from it.

## Global Constraints

- Non-commercial use only; never commit `build/` or any TGMC-derived art.
- OpenRA and TGMC stay pinned to the commits in `mod/bootstrap.py`.
- Nothing is committed beyond the spec and this plan until the user approves. Execution commits happen only after that approval.
- Success criteria from the spec: `mod/lint_static.py` reports 0 errors, `mod/check_mod.sh` passes, new scenario tests pass, `mod/smoke.sh` reports no exception log.
- Under-attack alerts: at most one per 250 ticks per player.
- Stance hotkeys are the OpenRA defaults: `StanceAttackAnything` (A Alt), `StanceDefend` (S Alt), `StanceReturnFire` (D Alt), `StanceHoldFire` (F Alt). Do not rebind them.
- Retreat hotkey: `TgmcRetreat` on V. Confirm V is unbound in `build/OpenRA/mods/common/hotkeys/game.yaml` and `tgmc/hotkeys.yaml` before Task 2 (Pre-flight row).

## Review Focus

1. Retreat when the chosen return point is destroyed mid-move: units must not stall or crash. Expected: they retarget the next nearest return point or stop cleanly.
2. Retreat or stance order on a mixed selection that includes non-combat units (builders, harvesters) with no `AutoTarget` or no `Retreat` trait: the order must apply to the units that can take it and ignore the rest, not fail the whole selection.
3. Shift-queued ability whose unit dies before the queued use: the queue must end without an exception.
4. Damage events that are not enemy attacks (friendly fire, self-damage, healing, zero damage): no alert. Expected: only positive damage from an enemy attacker alerts.
5. Retreat order given while Shift is held: must queue behind current orders, not replace them.

Each line is pinned by a test in the owning task (see Tasks 2, 3, 4).

---

## Pre-flight

Shared-interface rows (the task that produces what another task consumes):

| Producer | Consumer | Found | Ruling |
|---|---|---|---|
| Task 1: `CMD_AGGRESSIVE` button id | Task 6: restyle positions | Chrome restyle must not move this button out of the 3rd row | Restyle keeps button ids and relative rows. Cost if wrong: one YAML coordinate change. |
| Task 2: `CMD_RETREAT` button id, `ReturnPoint` trait | Task 6: restyle | Same | Same ruling. |
| Task 3: `Order.Queued` honoured in `ActiveAbility.ResolveOrder` | none | No direct dependency | Recorded for completeness. |
| Task 2: `TgmcEventLog` unchanged | Task 4: `TgmcEventLog.PostLimited` added | Task 4 adds a method, does not change `Post` | No interface break. |

Self-consistency: the spec names the Retreat trait `RetreatOrder` in one place and `Retreat` in another. Ruling: trait class `Retreat` (YAML key `Retreat`), order string `TgmcRetreat`. Cost if wrong: rename only.

Files already present and verified in the repo:
- `tgmc/code/Events.cs` `CommandCardLogic`: stance loop at roughly lines 207-217 (`CMD_GUARD`, `CMD_RETURN`, `CMD_HOLD`); ability buttons at roughly lines 258-260.
- `tgmc/code/CasteAbilities.cs` `ActiveAbility`: `IResolveOrder.ResolveOrder` at roughly lines 143-147 currently ignores `order.Queued`.
- `tgmc/code/Events.cs` `TgmcEventLog.Post(World, Player, string, WPos)` at roughly line 60.
- `tgmc/chrome/ingame-player.yaml`: `COMMAND_CARD` at roughly line 1007; `CMD_ABILITY1` and `CMD_ABILITY2` at roughly lines 1080-1094.
- `tgmc/hotkeys.yaml`: `TgmcAbility1` (R), `TgmcAbility2` (T).
- Return-point actors exist: `cryo-pod` (`tgmc/rules/structures.yaml`, roughly line 659), `medbay` (line 814), `resin-silo` (line 134), `forward-hive` (line 472).
- `Actor.QueueActivity(bool queued, Activity)` in `build/OpenRA/OpenRA.Game/Actor.cs` line 351.
- `Move` activity constructors in `build/OpenRA/OpenRA.Mods.Common/Activities/Move/Move.cs`.
- `Game.GetModifierKeys()` in `build/OpenRA/OpenRA.Game/Game.cs` line 327.
- Existing `ScriptActorProperties` pattern: `tgmc/code/CasteAbilities.cs` line 323 (`ActiveAbilityProperties`).

---

## Task 1: Attack Anything button and stance hotkeys

**Files:**
- Modify: `tgmc/code/Events.cs` (stance loop in `CommandCardLogic`)
- Modify: `tgmc/chrome/ingame-player.yaml` (add `CMD_AGGRESSIVE` button; add `Key:` to the four stance buttons)
- Create: `mod/scenarios/test-stance.lua`
- Modify: `mod/make_placeholders.py` (`SCENARIOS` entry `scenario-stance`)

**Interfaces:**
- Consumes: existing `AutoTarget` trait on `^Unit`, `SetUnitStance` order, `UnitStance` enum.
- Produces: button id `CMD_AGGRESSIVE` (used by Task 6).

- [ ] **Step 1: Verify inheritance.** Confirm every combat unit in `tgmc/rules/units.yaml` and the SOM units inherits `AutoTarget` from `^Unit`. Expected: a grep that lists no combat unit missing `AutoTarget`. If one is missing, add `AutoTarget` to it as its own ledgered ruling.

- [ ] **Step 2: Write the failing scenario test.** `mod/scenarios/test-stance.lua` sets Hold Fire on one Marine, one SOM trooper and one Xeno, places an enemy in range, and prints `TEST stance PASS` only if the Hold Fire unit does not fire and an Attack Anything unit does. Register the map as `scenario-stance` in `SCENARIOS` with `_scenario("test-stance", ...)`.

- [ ] **Step 3: Run it, expect FAIL.** Generate maps with `mod/make_placeholders.py`, build with `mod/build_mod.sh`, run `mod/test_scenarios.sh`. Expected: `TEST stance FAIL` or a missing-property error, because `Stance` is not reachable through the new button path yet.

- [ ] **Step 4: Add the button.** In `tgmc/chrome/ingame-player.yaml`, add `Button@CMD_AGGRESSIVE` at X 0, Y 108, Width 72, Height 30, `Background: sidebar-button`, `Text: cmd-aggressive` (fluent key already exists). Add `Key:` lines `StanceAttackAnything`, `StanceDefend`, `StanceReturnFire`, `StanceHoldFire` to the four stance buttons.

- [ ] **Step 5: Wire the click.** In `CommandCardLogic`, add `("CMD_AGGRESSIVE", UnitStance.AttackAnything)` to the stance tuple array.

- [ ] **Step 6: Run the scenario, expect PASS.** `TEST stance PASS`.

- [ ] **Step 7: Lint and chrome check.** `python3 mod/lint_static.py` (0 errors) and `mod/check_mod.sh` (passes).

- [ ] **Step 8: Commit.**
```bash
git add tgmc/code/Events.cs tgmc/chrome/ingame-player.yaml mod/scenarios/test-stance.lua mod/make_placeholders.py
git commit -m "Attack Anything stance button and stance hotkeys on the command card"
```

---

## Task 2: Retreat order

**Files:**
- Create: `tgmc/code/Retreat.cs` (`ReturnPoint`, `Retreat` traits; `Retreat` script properties)
- Modify: `tgmc/rules/structures.yaml` (add `ReturnPoint:` to `cryo-pod`, `medbay`, `resin-silo`, `forward-hive`)
- Modify: `tgmc/rules/units.yaml` (add `Retreat:` to `^Unit`)
- Modify: `tgmc/hotkeys.yaml` (add `TgmcRetreat: V`)
- Modify: `tgmc/code/Events.cs` (`CMD_RETREAT` button issues `TgmcRetreat`)
- Modify: `tgmc/chrome/ingame-player.yaml` (add `Button@CMD_RETREAT` at X 76, Y 108, 72x30)
- Create: `mod/scenarios/test-retreat.lua`, `mod/scenarios/test-retreat-none.lua`
- Modify: `mod/make_placeholders.py` (`scenario-retreat`, `scenario-retreat-none`)

**Interfaces:**
- Consumes: `Order` with `Queued` flag (engine), `Move` activity (engine).
- Produces: `ReturnPoint` trait (marker); `Retreat` trait resolving order string `TgmcRetreat`; script property `Retreat()` returning bool; button id `CMD_RETREAT` (used by Task 6).

- [ ] **Step 1: Write failing scenario tests.** `test-retreat.lua`: one unit of each faction (Marines, SOM, Xenos), a return point of each owned by the player, order `TgmcRetreat` via the `Retreat()` script property, print `TEST retreat PASS` once all three arrive within 1500 ticks, else FAIL. `test-retreat-none.lua`: no return point owned; call `Retreat()`; expect it returns false and the unit's position is unchanged after 100 ticks; print `TEST retreat-none PASS` or FAIL.

- [ ] **Step 2: Run them, expect FAIL.** `mod/test_scenarios.sh`. Expected: failures, because the trait does not exist (Lua error on `Retreat`).

- [ ] **Step 3: Implement the traits.** In `tgmc/code/Retreat.cs`:
  - `ReturnPointInfo : TraitInfo`, `ReturnPoint : ITraitInfo` marker.
  - `RetreatInfo : ConditionalTraitInfo`, `Retreat : ConditionalTrait<RetreatInfo>, IResolveOrder` for order string `TgmcRetreat`.
  - Resolution: among `World.ActorsWithTrait<ReturnPoint>()` owned by an ally of `self.Owner`, pick the nearest by `(CenterPosition - self.CenterPosition).LengthSquared`. None found: return without action (refused). Found: `self.QueueActivity(order.Queued, new Move(self, cell))` where `cell` is the nearest return point's cell. Use plain `Move` (no attack-move), so the unit does not stop to fight.
  - `Retreat()` script property (follow `ActiveAbilityProperties` at `CasteAbilities.cs` line 323) runs the same resolution and returns whether a target was found.

- [ ] **Step 4: Add YAML.** `ReturnPoint:` on the four structures; `Retreat:` on `^Unit`. `TgmcRetreat: V` in `tgmc/hotkeys.yaml` with the standard `Description`, `Types: World`, `Contexts: player` lines.

- [ ] **Step 5: Add the button.** `Button@CMD_RETREAT` in the chrome with `Key: TgmcRetreat`. In `CommandCardLogic`, `Issue` an order named `TgmcRetreat` to selected actors that have the `Retreat` trait, with the queued flag set from Shift (same rule as Task 3).

- [ ] **Step 6: Run the tests, expect PASS.** Both `TEST retreat PASS` and `TEST retreat-none PASS`.

- [ ] **Step 7: Review Focus coverage.** Add a test for Review Focus item 1: extend `test-retreat.lua` to destroy the nearest return point after 50 ticks and assert the unit still reaches the second one. Watch it fail, then pass.

- [ ] **Step 8: Lint, check, commit.**
```bash
python3 mod/lint_static.py && mod/check_mod.sh
git add tgmc/code/Retreat.cs tgmc/rules tgmc/hotkeys.yaml tgmc/code/Events.cs tgmc/chrome/ingame-player.yaml mod/scenarios mod/make_placeholders.py
git commit -m "Retreat order to the nearest friendly return point, with button and V hotkey"
```

---

## Task 3: Shift-queued abilities

**Files:**
- Modify: `tgmc/code/CasteAbilities.cs` (`ActiveAbility.ResolveOrder`; new small `UseAbilityActivity`)
- Modify: `tgmc/code/Events.cs` (ability buttons, around lines 258-260, pass Shift as the queued flag)
- Create: `mod/scenarios/test-queued-ability.lua`
- Modify: `mod/make_placeholders.py` (`scenario-queued-ability`)

**Interfaces:**
- Consumes: `Order.Queued`, `Actor.QueueActivity(bool, Activity)`, `Game.GetModifierKeys()`.
- Produces: script properties `QueueAbility(slot)` and `AbilityReady(slot)` on `ActiveAbilityProperties`.

- [ ] **Step 1: Failing test.** `test-queued-ability.lua`: a unit with an `ActiveAbility` in slot 1 (confirm the unit name in `tgmc/rules/units.yaml` before writing the test) moves toward a far point; call `QueueAbility(1)` during the move; assert the ability fires only after the move completes. Also queue a second ability that is on cooldown; assert the queue continues and no exception occurs. Print PASS or FAIL.

- [ ] **Step 2: Run, expect FAIL.** Expected: the ability fires immediately, because `ResolveOrder` ignores `Queued`.

- [ ] **Step 3: Implement.** In `ResolveOrder`: if `order.Queued`, call `self.QueueActivity(true, new UseAbilityActivity(this))`; otherwise keep `Use(self)`. `UseAbilityActivity` calls `Use` when reached, whether or not it succeeds, and then finishes. Ability buttons (Events.cs) pass `Game.GetModifierKeys()` Shift as the queued flag in place of the current `false`.

- [ ] **Step 4: Run, expect PASS.** Both cases print PASS.

- [ ] **Step 5: Review Focus item 3.** Add a test: queue the ability, kill the unit before it fires, assert no Lua error in the log (`grep -c LuaException game.log` is 0). Watch it fail, then pass.

- [ ] **Step 6: Lint, check, commit.**
```bash
python3 mod/lint_static.py && mod/check_mod.sh
git add tgmc/code/CasteAbilities.cs tgmc/code/Events.cs mod/scenarios mod/make_placeholders.py
git commit -m "Shift-queue ability hotkeys and buttons behind current orders"
```

---

## Task 4: Under-attack alert

**Files:**
- Modify: `tgmc/code/Events.cs` (`TgmcEventLog.PostLimited`, cooldown per player per key)
- Create: `tgmc/code/Alerts.cs` (`AlertOnDamage` trait, `INotifyDamage`)
- Modify: `tgmc/rules/units.yaml` (`AlertOnDamage:` on `^Unit`)
- Create: `mod/scenarios/test-alert.lua`
- Modify: `mod/make_placeholders.py` (`scenario-alert`)

**Interfaces:**
- Consumes: `TgmcEventLog.Post`, `RadarPings`, `INotifyDamage` (engine).
- Produces: `TgmcEventLog.PostLimited(World, Player, string key, WPos, int cooldownTicks)`; script player property `EventCount(key)` reads `TgmcEventLog.Count`.

- [ ] **Step 1: Failing test.** `test-alert.lua`: an enemy attacks one marine three times within 100 ticks; assert `EventCount("event-under-attack")` is 1 and a radar ping was produced. Print PASS or FAIL.

- [ ] **Step 2: Run, expect FAIL.** Expected: `EventCount` missing, or count 0.

- [ ] **Step 3: Implement.** `PostLimited` stores the last-post tick per (player, key) and skips posting inside `cooldownTicks` (250 in the caller). `AlertOnDamage.Damaged`: only when `e.Damage.Value > 0` and the attacker's owner is an enemy of `self.Owner`; calls `PostLimited` with `"event-under-attack"` and adds a ping through `RadarPings`.

- [ ] **Step 4: Run, expect PASS.**

- [ ] **Step 5: Review Focus item 4.** Add to the test: friendly fire and healing produce no additional entries. Watch it fail, then pass.

- [ ] **Step 6: Add the fluent key.** `event-under-attack` in `tgmc/fluent/tgmc.ftl`. Run `python3 mod/lint_static.py` (0 errors).

- [ ] **Step 7: Commit.**
```bash
git add tgmc/code/Events.cs tgmc/code/Alerts.cs tgmc/rules/units.yaml tgmc/fluent/tgmc.ftl mod/scenarios mod/make_placeholders.py
git commit -m "Under-attack alert, rate-limited to one per 250 ticks per player"
```

---

## Task 5: Full scenario run

**Files:** none new.

- [ ] **Step 1: Run.** `mod/test_scenarios.sh`. Expected: every `TEST ... PASS` line for stance, retreat, retreat-none, queued-ability and alert, and the existing scenarios still pass.

- [ ] **Step 2: Fix any regressions** under superpowers:systematic-debugging. Commit each fix separately.

- [ ] **Step 3: Record.** Write the pass lines into the ledger as `Task 5: complete`.

---

## Task 6: HUD restyle (design C, YAML only)

**Files:**
- Modify: `tgmc/chrome/ingame-player.yaml` only. Do not touch the Codex, Help or Stats panels. Do not change `ingame.yaml` unless a background name is missing.

**Interfaces:**
- Consumes: `CMD_AGGRESSIVE` (Task 1), `CMD_RETREAT` (Task 2).
- Produces: none.

Split into three chrome steps so each can be checked by screenshot. After each step run `mod/smoke.sh` and take a 1280x720 screenshot and a smaller one.

- [ ] **Step 1: DOCK and command card.** Make `DOCK` transparent. Radar bottom left; `SELECTION_PANEL`, `GROUP_PANEL` and `COMMAND_CARD` grouped bottom centre. `COMMAND_CARD` gets `Background: tgui-card`. Confirm the chrome arithmetic syntax (`WINDOW_WIDTH`, parentheses) on the first edit, as the spec's Risks section requires. Expected: `mod/smoke.sh` reports no exception log.

- [ ] **Step 2: BUILD_PANEL and TOP_BAR.** `BUILD_PANEL` to the right edge; `TOP_BAR` top right. Expected: smoke clean.

- [ ] **Step 3: EVENT_LOG and SUPPORT_POWERS.** `EVENT_LOG` top left as alert toasts; shift `SUPPORT_POWERS` right to clear it. Expected: smoke clean, and Codex, Help and Stats still open and close.

- [ ] **Step 4: Commit each step separately.**
```bash
git add tgmc/chrome/ingame-player.yaml
git commit -m "HUD: floating command dock (design C), step <1-3>"
```

---

## Final checks

- [ ] `python3 mod/lint_static.py` reports 0 errors.
- [ ] `mod/check_mod.sh` passes.
- [ ] `mod/test_scenarios.sh` prints PASS for every new scenario.
- [ ] `mod/smoke.sh` reports no exception log.
- [ ] Human check of the HUD screenshots (spec testing item 5). An executor cannot close this alone; hand it to the user.
