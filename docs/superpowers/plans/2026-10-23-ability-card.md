# Ability Card and Unit Kits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Warcraft-3 style 4x3 command card that shows the selected unit's abilities, four new ability mechanics (click-aim, toggle, aura, dash), and a TGMC-derived ability kit with fitting effects for every buildable unit.

**Architecture:** Everything extends the existing `ActiveAbility` trait (`tgmc/code/CasteAbilities.cs`) with new optional fields, so old abilities keep working unchanged. The card replaces `CommandCardLogic` (`tgmc/code/Events.cs:200`) and `Background@COMMAND_CARD` (`tgmc/chrome/ingame-player.yaml:1033`). Kits are pure YAML in `tgmc/rules/units.yaml` / `weapons.yaml` on top of those mechanics.

**Tech Stack:** OpenRA bleed (C#, `build/OpenRA`), mod code `tgmc/code`, MiniYaml rules, Lua 5.1 scenario tests.

**Spec:** `docs/superpowers/specs/2026-10-23-ability-card-design.md`

## Global Constraints

- Build: `export PATH=$HOME/TGMC/build/tools/dotnet:$PATH DOTNET_ROOT=$HOME/TGMC/build/tools/dotnet; TGMC=$HOME/TGMC/build/terragov-marine-corps OPENRA_DIR=$HOME/TGMC/build/OpenRA sh mod/build_mod.sh` must exit 0.
- Lint: `cd build/OpenRA && sh utility.sh tgmc --check-yaml` — 0 errors (45 warnings today; no new ones).
- Tests: scenario per mechanic in `mod/scenarios/test-<name>.lua` + an entry `scenario-<name>` in `mod/make_placeholders.py` `SCENARIOS`; run with `sh $S/run_scn.sh scenario-<name> <name> <sec>` after `cp -rf build/dev-maps/. $S/gen/dev-maps/` (S = session scratchpad). Each prints `TEST <name> PASS|FAIL (...)`.
- Lua 5.1: no `//`, use `math.floor`.
- Old fields and defaults of `ActiveAbilityInfo` keep their meaning; existing 25 abilities need no YAML edit except `Slot` values.
- Slots: 1-8. Hotkeys by slot: 1-4 = Q W E R, 5-8 = Z X C V (`TgmcAbility1`..`TgmcAbility8` in `tgmc/hotkeys.yaml`).
- Numbers are first guesses (spec non-goal: balance). Text labels, no new icons.
- Commit only when the user asks (user rule overrides the per-task commit steps of the template: replace "Commit" with "leave uncommitted, note files changed").
- Code style: match `CasteAbilities.cs` — `[Desc]` on every new field, one-line why-comments only.

## Review Focus

1. Mixed selection (e.g. squad leader + 5 riflemen): card must show the majority type's abilities and the button must fire only for units that have that ability ready — test in Task 1 (`card-mixed`).
2. Aimed ability clicked out of range: unit walks into range, then fires; target dies or moves meanwhile: the ability is cancelled without spending cooldown — test in Task 2 (`ability-aim` case C).
3. Toggle group switching while the unit is mid-attack: the old armament stops, the new one fires on the next shot; no unit ends with two shell types on — test in Task 3.
4. Aura stacking: two leaders yelling the same order must not stack the buff, only refresh its time — test in Task 4.
5. Dash into a wall / off-map / onto water: unit stops at the last enterable cell, never ends inside a blocked cell — test in Task 5.

---

### Task 1: The 4x3 card and 8 slots

**Files:**
- Modify: `tgmc/code/CasteAbilities.cs` (Slot desc 1-8; `ActiveAbilityInfo` add `Description` string, default null)
- Modify: `tgmc/code/Events.cs:200-330` (`CommandCardLogic`)
- Modify: `tgmc/chrome/ingame-player.yaml:1033-1170` (`Background@COMMAND_CARD`)
- Modify: `tgmc/hotkeys.yaml` (replace `TgmcAbility1: R`, `TgmcAbility2: T` with `TgmcAbility1..8`), `tgmc/fluent/*` (hotkey descriptions, `cmd-stance-*`)
- Test: `mod/scenarios/test-card-slots.lua`, `mod/scenarios/test-card-mixed.lua`

**Interfaces:**
- Produces: `ActiveAbilityInfo.Slot` in 1..8; `ActiveAbilityInfo.Description` (tooltip line); chrome buttons `CMD_SLOT1`..`CMD_SLOT8`; `CommandCardLogic.CardType()` returns the `ActorInfo` name with most selected units (tie: first in selection).
- Lua (unchanged signature): `actor.UseAbility(slot)`, `actor.QueueAbility(slot)`, `actor.AbilityReady(slot)` accept 1..8.

- [ ] **Step 1: Write test `test-card-slots.lua`**: squad_leader with an enemy runner 6 cells away (HoldFire); at tick 10 `UseAbility(3)`; PASS if it returned true and the runner shows the Mark effect (read `TGMCMarkTarget` in weapons.yaml for what it grants; fall back to `runner.Health < runner.MaxHealth`). Scenario entry `scenario-card-slots`: size (32,24), `drop_conquest`, actors squad_leader Marines 10,10; runner Xenos 16,10; resin-silo Xenos 28,20; cryo-pod Marines 4,18.
- [ ] **Step 2: Run it.** Expected PASS (Lua already accepts any slot); it guards slot 3 through the card rewrite.
- [ ] **Step 3: Chrome**: 4x3 grid of 72x52 buttons, 4 px gap, at the old card spot (`X: PARENT_WIDTH - 318`, card grows to 3 rows). Row 1: `CMD_ATTACK`, `CMD_STOP`, `CMD_PATROL`, `CMD_STANCE`. Rows 2-3: `CMD_SLOT1`..`CMD_SLOT8` with `Key: TgmcAbility<n>`. Remove `CMD_ABILITY1/2`, `CMD_EVOLVE`, `CMD_DEVOLVE`, `CMD_RETREAT`, `CMD_MEDIC`, `CMD_INFECTED`, the four stance buttons. Button text: `"<KEY> <Label>"`, charges as `"x2"` on a second line.
- [ ] **Step 4: `CommandCardLogic`**: per frame, build the entry list for `CardType()`: its `ActiveAbility` traits ordered by Slot, then side entries — Evolve (if `EvolvesInfo.Next`), Devolve (if `Previous`), Retreat (if `Retreat` trait), Medic (only while `Selected().Any(NeedsMedic)`), Infected (only while `Infected().Any()`). Entry i goes to `CMD_SLOT(i+1)`; extras beyond 8 are not shown. Disabled = not ready; highlighted = `Active`; while cooling down the label shows remaining seconds. `CMD_STANCE` cycles AttackAnything → Defend → ReturnFire → HoldFire, text = current stance. Tooltip: reuse the chrome tooltip pattern already in the mod (grep `TooltipTemplate` in `tgmc/chrome`) with Label, Description, cooldown seconds.
- [ ] **Step 5: Slot check**: grep `Slot:` in units.yaml; confirm no unit has two abilities on one slot.
- [ ] **Step 6: Write `test-card-mixed.lua`**: squad_leader + 3 riflemen; call `UseAbility(1)` on each; PASS if only the squad leader's call returns true (Review Focus 1 at trait level).
- [ ] **Step 7: Build, lint, run `card-slots`, `card-mixed` and the 6 existing scenarios that call `UseAbility`** (`grep -l UseAbility mod/scenarios/*.lua`). Expected: all PASS.
- [ ] **Step 8: Visual check**: screenshot a game with a squad leader selected (`mod/shot_map.py`); send it to the user. Expected: 4x3 grid, row 1 commands, Smoke/Mirage/Mark/Retreat in row 2.

### Task 2: Click-aimed abilities (`Aim: Target`, `Aim: TargetActor`)

**Files:**
- Modify: `tgmc/code/CasteAbilities.cs` (enum, `ResolveOrder`, `Use`, activity, Lua properties), `tgmc/code/Bots.cs:549-570` (AbilityBotModule)
- Create: `tgmc/code/AbilityTargeting.cs` (order generator)
- Modify: `tgmc/code/Events.cs` (button click enters targeting for aimed abilities)
- Test: `mod/scenarios/test-ability-aim.lua`

**Interfaces:**
- Consumes: Task 1 slot buttons.
- Produces: `AbilityAim.Target`, `AbilityAim.TargetActor`; `ActiveAbilityInfo.TargetRelationships` (PlayerRelationship, default Enemy, for TargetActor); `ActiveAbility.UseAt(Actor self, Target target) : bool`; `AbilityOrderGenerator(World world, IEnumerable<Actor> casters, string orderName, WDist range)` — left click issues `new Order(orderName, caster, target, queued)` per caster, right click / Escape cancels, cursor `ability` in range / `move` out of range, draws the range circle around the first caster; Lua `actor.UseAbilityAt(slot, cpos) : bool`, `actor.UseAbilityOn(slot, actor) : bool`, `actor.AbilityAim(slot) : string`.

- [ ] **Step 1: Failing test `test-ability-aim.lua`**: test ability added through `extra_rules` on rifleman (`ActiveAbility@testaim`, `Aim: Target`, `Range: 5c0`, `Slot: 1`, `Cooldown: 50`, `Weapon:` the mod's grenade weapon — grep weapons.yaml for `Grenade`). Case A: runner (HoldFire) 4 cells away; `UseAbilityAt(1, runner.Location)`; pass if runner hurt within 30 ticks. Case B: second runner 9 cells away; `UseAbilityAt(1, thatCell)`; pass if rifleman ends within 5 cells of it and it is hurt by tick 200. Case C: `UseAbilityOn` a TargetActor variant at a far runner, kill that runner by Lua before arrival; pass if `AbilityReady` stays true (no cooldown spent).
- [ ] **Step 2: Run, expect FAIL** (`UseAbilityAt` is nil).
- [ ] **Step 3: Implement `UseAt`**: out of `Range` → queue `IMove.MoveWithinRange(target, range)` then a `UseAbilityActivity` carrying the target; on arrival re-check the target, cancel without cooldown if invalid. `Use(self)` with Target/TargetActor and no target returns false. `ResolveOrder` reads `order.Target` for these aims.
- [ ] **Step 4: Card + order generator**: clicking an aimed ability button sets `world.OrderGenerator = new AbilityOrderGenerator(...)`, highlighted while active (same pattern as `AttackMoveOrderGenerator`, `Events.cs:285`).
- [ ] **Step 5: Bot**: Target aims → cell of the enemy with most enemies within 2 cells inside `AiRange`; TargetActor → nearest valid actor by `TargetRelationships` (with `AiWoundedPercent > 0`: the most hurt ally). Issue `new Order(OrderName, unit, Target.FromCell/FromActor, false)`.
- [ ] **Step 6: Build, lint, run `ability-aim` and Task 1 tests** — PASS.

### Task 3: Toggles (`Toggle`, `Group`)

**Files:**
- Modify: `tgmc/code/CasteAbilities.cs`
- Test: `mod/scenarios/test-ability-toggle.lua`

**Interfaces:**
- Produces: `ActiveAbilityInfo.Toggle` (bool, false), `Group` (string, null), `StartOn` (bool, false). With `Toggle: true`, `Use` switches `Condition` on/off (Duration ignored) and `Active` reports on. Turning one on turns off the others of the same `Group` on that actor; a grouped toggle cannot be switched off directly (one is always on); a group with no `StartOn` member starts with its lowest-Slot member on. Cooldown applies on switching on. Lua `actor.AbilityActive(slot) : bool`.

- [ ] **Step 1: Failing test**: mortarman via `extra_rules` with `@he` (`Toggle: true`, `Group: shell`, `Condition: shell-he`, `StartOn: true`, Slot 1) and `@smoke` (`Group: shell`, `Condition: shell-smoke`, Slot 2), two `Armament`s gated by those conditions (`TGMCMortar` and the mod's smoke weapon). Asserts: start he=true smoke=false; after `UseAbility(2)` he=false smoke=true; after `UseAbility(2)` again smoke=true he=false (Review Focus 3).
- [ ] **Step 2: Run, expect FAIL** (`AbilityActive` nil).
- [ ] **Step 3: Implement** toggle in `Use`, group default in `INotifyCreated.Created`, Lua `AbilityActive`.
- [ ] **Step 4: Build, lint, run `ability-toggle` + earlier tests** — PASS.

### Task 4: Auras and the leader yell

**Files:**
- Modify: `tgmc/code/CasteAbilities.cs`, the `Fx` helper (grep `static class Fx`), `tgmc/rules/units.yaml` (`^Infantry`, `^Xeno`, mech bases: `ExternalCondition` + modifiers for aura conditions)
- Test: `mod/scenarios/test-ability-aura.lua`

**Interfaces:**
- Produces: `ActiveAbilityInfo.AuraRange` (WDist, 0 = off), `AuraCondition` (string), `AuraDuration` (int ticks), `AuraRelationships` (default Ally), `AuraIncludesSelf` (bool, true), `Shout` (string floating over the user, e.g. `MOVE!`), `ShoutColor` (Color, FFD040), `Ring` (Color, unset = no ring). `Fx.Shout(World world, Actor actor, string text, Color color)`; `Fx.Ring(World world, WPos pos, WDist radius, Color color)` — circle expanding from 0 to radius over 15 ticks. Re-granting refreshes the time and never stacks (one token per aura condition per target). Lua `actor.HasAuraCondition(string name) : bool`, `actor.AuraStacks(string name) : int`.

- [ ] **Step 1: Failing test**: squad_leader with test ability `Slot: 4`, `Aim: Self`, `AuraRange: 6c0`, `AuraCondition: order-move`, `AuraDuration: 150`, `Shout: MOVE!`; a second squad_leader with the same; rifleman at 3 cells and one at 10 cells. After both leaders `UseAbility(4)`: near `HasAuraCondition("order-move")` true, far false, near `AuraStacks("order-move") == 1` (Review Focus 4); after tick 170 near false.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** the aura grant in `Use`, `Fx.Shout` (reuse the renderer in `FloatingText.cs`), `Fx.Ring`.
- [ ] **Step 4: Aura conditions on the bases**: `order-move` → `SpeedMultiplier: 125`; `order-hold` → `DamageMultiplier: 75`; `order-focus` → `InaccuracyMultiplier: 60` + `FirepowerMultiplier: 110`; `screech-heal` → `ChangesHealth` +2%/s; `screech-frenzy` → `FirepowerMultiplier: 120`; `stim` → `SpeedMultiplier: 130` + `ChangesHealth` +1%/s. Each with a small tint or `StatusLabel` so the buff is visible.
- [ ] **Step 5: Build, lint, run `ability-aura` + earlier tests** — PASS.

### Task 5: Dashes and charges

**Files:**
- Modify: `tgmc/code/CasteAbilities.cs`, `tgmc/code/Knockback.cs` (`Thrown`: make it usable from `CasteAbilities.cs`)
- Test: `mod/scenarios/test-ability-dash.lua`

**Interfaces:**
- Produces: `ActiveAbilityInfo.ChargeDistance` (WDist, 0 = off), `ChargeTicks` (int, 10), `ChargeHeight` (WDist, 0; 512 for pounces), `ChargeTrail` (string effect image, null), `ChargeHitThrow` (WDist, 0 = no knock-aside). With `Aim: Target` the unit dashes toward the clicked cell up to `ChargeDistance`, else straight ahead; it stops at the last cell it can enter; `Weapon` hits each enemy it passes or stops against.

- [ ] **Step 1: Failing test**: rifleman via `extra_rules` with a dash ability (`ChargeDistance: 5c0`, `Aim: Target`, a melee weapon). Case A: runner on the path → ends ≥4 cells from start, runner hurt. Case B: cade 2 cells ahead → ends on the cell before the cade (Review Focus 5). Case C: target cell beyond the map edge → ends on the edge cell.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** with the `Thrown` movement.
- [ ] **Step 4: Build, lint, run `ability-dash` + earlier tests** — PASS.

### Task 6: Marine kits with effects

**Files:**
- Modify: `tgmc/rules/units.yaml` (marine units in the spec's list), `tgmc/rules/structures.yaml` (mortar-emplacement, artillery-emplacement), `tgmc/rules/weapons.yaml` (shell/rocket/grenade/effect weapons), `tgmc/audio` + its sound list (TGMC sounds from `build/terragov-marine-corps/sound`: e.g. `effects/pred_cloakon.ogg`, `mecha/overboost_chargeup.ogg`; leader shouts from TGMC's voice sounds if present, else the mod's `MarineVoice` set)
- Test: `mod/scenarios/test-kits-marines.lua`

**Interfaces:**
- Consumes: Tasks 1-5 fields and Lua functions.
- Produces (per spec): leader orders SL `@move/@hold/@focus` (`AuraRange: 6c0`, `AuraDuration: 250`, `Cooldown: 900`, `Shout: MOVE!/HOLD!/FOCUS!`, gold `Ring`, shout sound); FC the same with `AuraRange: 9c0`. Shell toggles `Group: shell`, rocket toggles `Group: rocket`, grenade toggles `Group: grenade`. Mech: `@overboost` (dash 4c0, spark trail), `@assaultarmor` (Self burst 2c0, ring + lightning effect), `@cloak` (toggle, `Cloak` gated by condition), `@pulsearmor` (`DamageMultiplier: 30` for 60 ticks, blue tint), `@legoverload` (toggle: speed 140%, `ChangesHealth` -1%/s), `@smoke` (Self smoke weapon), `@barrage` (Target, 8c0, rocket pod weapon x4). Shell impacts per spec "Effects" (fire, white smoke, purple, flare light + a temporary `RevealsShroud` actor for 300 ticks).

- [ ] **Step 1: Failing test**: one of every marine unit + both emplacements, HoldFire xeno dummies in range; for each unit and each slot with an ability, use it per `AbilityAim(slot)` (Self/Nearest/Forward → `UseAbility`, Target → `UseAbilityAt(dummy cell)`, TargetActor → `UseAbilityOn(dummy or hurt ally)`); toggles must flip `AbilityActive`. PASS if every unit has ≥1 ability and every use returned true; on FAIL print the `unit:slot` list.
- [ ] **Step 2: Run, expect FAIL** (units without abilities).
- [ ] **Step 3: Add kits, effects, sounds.**
- [ ] **Step 4: Build, lint, run `kits-marines` + all earlier tests** — PASS.
- [ ] **Step 5: Screenshots**: squad leader yelling MOVE! (text + ring), mortar firing incendiary; send to the user.

### Task 7: Xeno kits with effects

Same shape as Task 6 for the spec's xeno list (runner, hunter, drone, boiler, bull, sentinel, warrior, spitter, queen, facehugger). Plasma costs: TGMC's `plasma_cost` from `$S/tgmc-src/code/modules/mob/living/carbon/xenomorph/castes/<caste>/abilities_<caste>.dm`, scaled to the mod's `Plasma.Max: 100` against that caste's TGMC plasma max. Test `mod/scenarios/test-kits-xenos.lua`, same assertions vs marine dummies, plasma full via `extra_rules` (`Plasma: StartPercent: 100`). Screenshots: boiler bombard, bull charge.

- [ ] Step 1 failing test · Step 2 FAIL · Step 3 kits + effects · Step 4 build/lint/all tests PASS · Step 5 screenshots

### Task 8: SOM kits

Each SOM unit gets its marine counterpart's `ActiveAbility@*` blocks (SOM units do not inherit marine actors — copy). SOM rocketeer group: HEAT / Thermobaric / Radiation. som_mech gets the mech kit through `Inherits: mech` (verify). som_scout: Cloak toggle; som_veteran: Sprint (Self, speed 140% for 100 ticks). Test `mod/scenarios/test-kits-som.lua`, same assertions.

- [ ] Step 1 failing test · Step 2 FAIL · Step 3 kits · Step 4 build/lint/all tests PASS

### Task 9: Whole-suite regression and AI check

- [ ] **Step 1:** `sh $S/suite.sh` (xargs -P3): every scenario that passed before still passes; fix the root cause of any new non-PASS.
- [ ] **Step 2:** AI vs AI (`balance-aivai`) for 3 game minutes with a Lua counter; expected ≥1 aimed use, ≥1 aura, ≥1 dash by bots.
- [ ] **Step 3:** Report to the user with screenshots; leave uncommitted unless asked.
