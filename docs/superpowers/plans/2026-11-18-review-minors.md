# Review Minors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the seven minor findings of the 2026-11-17 code review of the uncommitted TGMC work.

**Architecture:** Five small, separate fixes in the mod's C# (`tgmc/code/`) and one bot rule (`tgmc/rules/ai.yaml`). The plan changes no game design. Each task is built and tested alone.

**Tech Stack:** C# OpenRA mod traits (.NET from `build/tools/dotnet`), OpenRA yaml rules, Lua scenario tests.

**Spec:** the review's minor list (session of 2026-11-17, summarised here, since no spec file exists):
1. Pain and medic cries play for units under fog.
2. The wall damage overlay shows live damage on fogged cells.
3. `DropPodPowerInfo.FactionActors` and `BeaconActors` names are not checked by lint.
4. Formation pace uses `Info.Speed`, ignoring speed modifiers (sticky resin, gas).
5. `TgmcVoiced` holds `static World lastWorld`, which keeps the last game's world alive.
6. `OnWeedsConditionInfo.Interval: 0` divides by zero (`ActorID % Interval`).
7. Xeno drones are contended in `ai.yaml`: `FieldBotModule@xenos-corrupt` and `WeedDroneBotModule@xenos` both order idle drones.

## Global Constraints

- Build: `PATH=$PWD/build/tools/dotnet:$PATH DOTNET_ROOT=$PWD/build/tools/dotnet TGMC=$PWD/build/terragov-marine-corps OPENRA_DIR=$PWD/build/OpenRA sh mod/build_mod.sh`. Always the full build, never an rsync overlay.
- Lint: `sh mod/check_mod.sh`. Tests: `OPENRA_DIR=$PWD/build/OpenRA sh mod/test_scenarios.sh [secs] [names]`.
- No commit, push or release unless the user asks. Never commit `build/`. The steps below have no commit step for this reason.
- Sound and render code is local and cosmetic. It must never change synced state. Use `Game.CosmeticRandom` or `world.LocalRandom` only.
- Comments in the house style: one line on the why. A known limit gets `shortcut: <limit>, <when to upgrade>`.

## Review Focus

- A player's own units under the fog of an ally's view: the owner always sees its own units, so its own cries still play. `World.FogObscures` is false for visible actors.
- A spectator or a replay with no render player: `FogObscures` is false when `RenderPlayer == null`, so the spectator hears and sees everything. That is the expected result.
- A wall damaged in view, then fogged, then broken further: it shows the last seen step until it is seen again. A wall repaired or turned to rubble in fog keeps its old overlay until seen.
- A formation member that leaves sticky resin mid-walk: the pace is taken once, at the order. Task 4 records this as a shortcut.
- A xeno bot with fewer idle drones than the field cap: every idle drone goes to a field and none grows weeds while free fields last. Task 5 checks the fields and weed-node counts on full maps.

---

### Task 1: Sounds: fog check on cries, and no world kept in memory

**Files:**
- Modify: `tgmc/code/Pain.cs:36-55` (`CriesInPain.Damaged`), `tgmc/code/Pain.cs:67-93` (`TgmcVoiced`)
- Modify: `tgmc/code/Infestation.cs:184` (the `Hugged` voice)

**Interfaces:** none shared.

- [ ] **Step 1:** In `CriesInPain.Damaged`, return before the cooldown is set when `self.World.FogObscures(self)` is true. The `next` cooldown is not spent on a cry nobody hears.
- [ ] **Step 2:** Guard `self.PlayVoiceLocal("Hugged", 1f)` in `Infestation.cs` with the same check.
- [ ] **Step 3:** In `TgmcVoiced`, replace `static World lastWorld` with `static WeakReference<World> lastWorld`. The test becomes `lastWorld != null && lastWorld.TryGetTarget(out var w) && w == self.World && ...`. The set becomes `lastWorld = new WeakReference<World>(self.World)`. This only allocates when a throttled shout plays.
- [ ] **Step 4:** Build. Expected: `build 0`.
- [ ] **Step 5:** Run the scenarios that cover pain and voices (find them with `ls mod/scenarios | grep -i 'pain\|voice\|hug'`). Expected: PASS. No test can hear a sound, so the fog check is verified by reading the code.

### Task 2: Wall damage overlay shows what was last seen

**Files:**
- Modify: `tgmc/code/Walls.cs:43-110` (`DestructibleWalls`)

**Interfaces:** none shared. `damaged` stays the synced truth. The new field is render-only.

- [ ] **Step 1:** Add `readonly Dictionary<CPos, int> seen = []` (render-only: what the render player last saw).
- [ ] **Step 2:** In `RenderAboveWorld`, when `self.World.RenderPlayer == null`, draw from `damaged` as today. Otherwise, first update `seen` for every cell in `damaged.Keys` together with `seen.Keys` that is not `FogObscures(cell)`. If the cell is in `damaged`, `seen[cell] = damaged[cell]`. If not, remove it from `seen`. Then draw from `seen`. Copy the keys to a list before the loop, because the loop removes entries.
- [ ] **Step 3:** Fix the comment above `RenderAboveWorld`: it is drawn before the shroud, and fogged cells show the last step seen.
- [ ] **Step 4:** Build, then `sh mod/test_scenarios.sh 60 scenario-walls scenario-wall-grenade`. Expected: 2 of 2 passed.
- [ ] **Step 5:** No test can see the overlay. Record "fog overlay checked by code read" in the report.

### Task 3: Rule checks at load time (drop pod names, interval 0)

**Files:**
- Modify: `tgmc/code/DropPod.cs:21-69` (`DropPodPowerInfo`)
- Modify: `tgmc/code/Weeds.cs:258-280` (`OnWeedsConditionInfo`)

**Interfaces:** none shared.

- [ ] **Step 1:** Add `[ActorReference]` to `BeaconActors` (a `string[]`, which stock lint supports).
- [ ] **Step 2:** Stock lint reads dictionary values only when they are `string`, not `string[]` (`LintExts.GetFieldValues`). So in `DropPodPowerInfo`, override `RulesetLoaded(Ruleset rules, ActorInfo ai)`: call `base.RulesetLoaded`, then for every name in `FactionActors.Values` missing from `rules.Actors` throw `new YamlException($"DropPodPower on {ai.Name}: FactionActors names unknown actor '{name}'.")`. Check the base first with `grep -rn "RulesetLoaded" build/OpenRA/OpenRA.Mods.Common/Traits/SupportPowers/SupportPower.cs build/OpenRA/OpenRA.Mods.Common/Traits/Conditions/ConditionalTrait.cs`. If no virtual exists, implement `IRulesetLoaded` instead.
- [ ] **Step 3:** In `OnWeedsConditionInfo`, implement `IRulesetLoaded`: `if (Interval < 1) throw new YamlException($"OnWeedsCondition on {ai.Name}: Interval must be at least 1.");`.
- [ ] **Step 4:** Build, then make a negative check. Temporarily add `x` to the end of one SOM actor name inside `FactionActors` in `tgmc/rules/structures.yaml`. Run `sh mod/check_mod.sh`. Expected: it fails, naming the bad actor. Revert the edit. Do the same with `Interval: 0` on one `OnWeedsCondition` in `tgmc/rules/units.yaml`. Expected: fails with "Interval must be at least 1". Revert.
- [ ] **Step 5:** `sh mod/check_mod.sh`. Expected: `tgmc: checks passed`.

### Task 4: Formation pace counts speed modifiers

**Files:**
- Modify: `tgmc/code/TileStep.cs:136-165` (`FormationMoves.Flush`)
- Test: `mod/scenarios/test-formation.lua`

**Interfaces:**
- Produces: `int TgmcMobile.CurrentSpeed(Actor self)` in `TileStep.cs`. It returns `Info.Speed` with every `ISpeedModifier` on the actor applied except this `TgmcMobile`'s own, through `OpenRA.Mods.Common.Util.ApplyPercentageModifiers`.

- [ ] **Step 1: Write the failing test.** In `test-formation.lua`, inside the `Trigger.AfterDelay(10, ...)` before the move orders, add `crusher.GrantCondition("stuck", 3000)`. This is the `^Unit` `ExternalCondition@stuck`, `SpeedMultiplier` 50. The PASS line keeps `gap <= 50 and apart == 2 and near`. Add the stuck crusher to the header comment.
- [ ] **Step 2:** Build, then `sh mod/test_scenarios.sh 60 scenario-formation`. Expected: FAIL. The runner paces at the crusher's full speed and arrives far ahead, so `gap` is over 50.
- [ ] **Step 3:** Add `CurrentSpeed`. In `Flush`, use `m.Mobile.CurrentSpeed(m.Actor)` for `slowest` and `mobile.CurrentSpeed(actor)` as the divisor in `JoinFormation`. Keep the `> 0` guard on the divisor. Comment: `shortcut: pace is taken at the order; a member that leaves resin mid-walk keeps the old pace until its next order`.
- [ ] **Step 4:** Build, then `sh mod/test_scenarios.sh 60 scenario-formation`, run 3 times. Expected: PASS each time.

### Task 5: Xeno drones: no double orders

**Files:**
- Modify: `tgmc/code/Bots/FieldBotModule.cs` (Info gets `Max`, loop at :79 stops after it)
- Modify: `tgmc/code/Bots/WeedDroneBotModule.cs:63` (skip claimed drones)
- Modify: `tgmc/rules/ai.yaml:727-731` (`FieldBotModule@xenos-corrupt`), and the comment at `:126`

**Interfaces:**
- Produces: `FieldBotModuleInfo.Max` (`int`, default 0 = no cap): idle attackers sent per look.

Today both modules take idle drones in `world.Actors` order. `WeedDroneBotModule` skips the first `Spare: 2`, but `FieldBotModule@xenos-corrupt` sends every idle drone. So on the same look, drones 3 and up get a field order and a weed order, and the last one queued wins.

- [ ] **Step 1:** Add `[Desc("Idle attackers sent per look, 0 for all.")] public readonly int Max = 0;`. Break the attacker loop after `Max` orders when `Max > 0`.
- [ ] **Step 2:** Set `Max: 2` on `FieldBotModule@xenos-corrupt`, which matches `WeedDroneBotModule@xenos Spare: 2`. Add a one-line comment naming the pair. Both must stay equal.
- [ ] **Step 3:** Add `&& !BotUnits.Claimed(a)` to the drone filter in `WeedDroneBotModule`, so both modules see the same idle drones in the same order.
- [ ] **Step 4:** Build, then lint, then run the bot tests: `sh mod/test_scenarios.sh 120 $(ls mod/scenarios | sed -n 's/^test-\(ai-.*\)\.lua$/scenario-\1/p' | tr '\n' ' ')`. Expected: all pass.
- [ ] **Step 5:** Full maps: the 42 `aimap-*` maps with `test-aimap.lua`, `xargs -P4`, as on 2026-11-17. Expected: xeno `fields=` stays in the 2–8 range seen then, and xeno weed nodes do not drop. Record the marine–xeno decided count beside the earlier 21–9.

### Task 6: Whole check

- [ ] **Step 1:** Build, then `sh mod/check_mod.sh`, then the full `sh mod/test_scenarios.sh`. Expected: `build 0`, `tgmc: checks passed`, `171 of 171 passed`.
- [ ] **Step 2:** Report to the user what each task changed and what was checked only by reading (Task 1 sound, Task 2 overlay). Do not commit.
