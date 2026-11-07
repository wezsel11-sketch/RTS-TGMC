# Reactive AI Implementation Plan (Part A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Both TGMC bots remember where they saw enemy strength, defend whatever of theirs is attacked, raid the enemy's weak
spots and aim their main army at the weakest valuable target.

**Architecture:** One new player trait, `ThreatMemory`, keeps a faded grid of seen enemy strength and recent attacks on the
owner's actors. It ticks on its own (not as a bot module), so the scripted xeno player of Part B can use it too, and Lua reads it
through a player script property. Three new bot modules in `tgmc/code/Bots.cs` read it: `DefendBotModule`, `RaidBotModule`
and `AttackTargetBotModule`. They take units the same way the uncommitted `MinerGuardBotModule` does: out of the squad manager's
idle-base-unit list (`IBotNotifyIdleBaseUnits`), handing them back by re-adding them.

**Tech Stack:** OpenRA (C#, .NET 10, `OpenRA.Mods.Common` bot interfaces), YAML rules, Lua scenario tests.

**Spec:** `docs/superpowers/specs/2026-11-07-reactive-ai-and-evac-mission-design.md` (Part A).

## Global Constraints

- Skirmish bots only know what they saw: `ThreatMemory` counts an enemy actor only when `actor.CanBeViewedByPlayer(owner)`
  is true, or it is in the owner's frozen-actor layer. The one exception is a `FullVision: true` option, off by default, for the
  Part B mission xenos.
- Both factions get every module: marine bot (`!faction-xenos`) and xeno bot. Responses react to any enemy, human or bot.
- `FieldDefenseBotModule` is not touched.
- Existing scenario tests and the four survival maps keep passing.
- A balance shift is acceptable once measured and reported with `mod/balance.sh`. It is not a gate.
- Code style follows `tgmc/code/Bots.cs`: `[TraitLocation(SystemActors.Player)]`, `[Desc]` on every Info field,
  `ConditionalTrait<...Info>`, an `Interval` countdown, and a one-line YAML comment per module in `tgmc/rules/ai.yaml`.

## Build and test loop (every task uses it)

From `~/TGMC`, with `export PATH=$PWD/build/tools/dotnet:$PATH DOTNET_ROOT=$PWD/build/tools/dotnet`:

```bash
dotnet build tgmc/code/Tgmc.csproj -c Release -o build/tgmc-dll -p:OPENRA_BIN=$PWD/build/OpenRA/bin -nologo
cp build/tgmc-dll/Tgmc.dll build/OpenRA/bin/
rsync -a tgmc/ build/mod/tgmc/
python3 mod/build_sprites.py && python3 mod/make_placeholders.py   # same arguments as mod/build_mod.sh passes
SDL_VIDEODRIVER=offscreen OPENRA_DIR=$PWD/build/OpenRA mod/test_scenarios.sh 150 <name-part>
```

A scenario passes when its `build/scenarios/<map>/game.log` holds `TEST <name> PASS`. New scenario maps go in `SCENARIOS` in
`mod/make_placeholders.py`. New Lua tests go in `mod/scenarios/test-<name>.lua`, following `test-ai-retreat.lua`: print exactly
one `TEST <name> PASS (...)` or `TEST <name> FAIL (...)` line. If a step's command differs on this box (e.g. sprite builder
arguments), use what `mod/build_mod.sh` does and note it in the commit.

## Review Focus

1. **Actors vanish mid-response.** Xenos evolve (the actor is replaced), units die, miners get captured. Every stored `Actor`
   is checked for `IsDead`, `!IsInWorld` and a changed `Owner` before use, and dropped quietly. Test: Task 3's
   `ai-defend-victim-dies` case.
2. **No units to send.** A bot is attacked or wants to raid with an empty idle list. Nothing is ordered and nothing throws.
   Test: Task 3's `ai-defend-nobody` case.
3. **Nothing seen yet.** Early game, an empty memory. Raid and attack-target do nothing, and the stock squad behaviour runs
   unchanged. Test: Task 5's `ai-attack-weak` asserts no exception in `game.log` during the first 500 ticks.
4. **Big maps.** The TGMC conversions are large. The memory samples `world.Actors` once per `Interval` (default 25 ticks), not
   per cell, and the grid is sized from the map bounds. Test: Task 2 runs `scenario-ai-threat` on a 64x48 map and the run
   finishes inside the normal ceiling.
5. **Modules fighting over a unit.** Guards, defenders and raiders all come out of the same idle list, so a unit belongs to
   at most one module at a time. Test: Task 4's `ai-raid` asserts no raider is also listed as a miner guard (a debug count
   printed by the test).

---

### Task 1: Finish the miner guards

The uncommitted `MinerGuardBotModule` (`tgmc/code/Bots.cs`, `tgmc/rules/ai.yaml`) and the debug lines in
`mod/scenarios/test-ai-marine-fields.lua` are in the working tree, untested.

**Files:**
- Modify: `tgmc/code/Bots.cs` (`MinerGuardBotModule`, and `FieldBotModule`'s attacker loop near line 607)
- Modify: `tgmc/rules/ai.yaml` (`MinerGuardBotModule@marines`, check `Guards:` lists the marine fighter types)
- Modify: `mod/scenarios/test-ai-marine-fields.lua`

**Interfaces:**
- Produces: `MinerGuardBotModule.IsGuard(Actor a) -> bool`. Later modules skip guards with it.

- [ ] **Step 1:** Run the build loop and `test_scenarios.sh 400 ai-marine-fields`. Expected: it compiles. Read the
  `DBG field N: marine fighters within 8 cells` lines.
- [ ] **Step 2:** Add an assert to the test: once the marines have held a claimed field for 1000 ticks, at least 2 fighters
  are within 8 cells of it. Make it part of the existing PASS condition.
- [ ] **Step 3:** Fix whatever Step 1 or 2 shows. If the guard count is 0, check that `ai.yaml` sets `Guards:`.
- [ ] **Step 4:** Run `test_scenarios.sh 400 ai-marine-fields ai-fields ai-engineers`. Expected: all PASS. Remove the DBG
  lines or keep them behind the test's existing debug pattern.
- [ ] **Step 5:** Commit: "Marine bot keeps two fighters at each miner".

### Task 2: ThreatMemory

**Files:**
- Create: `tgmc/code/ThreatMemory.cs`
- Modify: `tgmc/rules/player.yaml` (add `ThreatMemory` to `Player`)
- Create: `mod/scenarios/test-ai-threat.lua`, plus a `scenario-ai-threat` map entry in `mod/make_placeholders.py`

**Interfaces:**
- Produces (C#, namespace `OpenRA.Mods.TGMC.Traits`):
  - `ThreatMemoryInfo : ConditionalTraitInfo` with `[TraitLocation(SystemActors.Player)]` and fields
    - `int Interval = 25`, sample period
    - `int CellSize = 4`, map cells per grid square
    - `int FadePercent = 90`, kept per sample
    - `bool FullVision = false`
    - `string[] Defences`, the types that count `DefenceWeight` percent of their cost (default `sentry-turret`, `cade`, plus the xeno defensive structures in `structures.yaml`)
    - `int DefenceWeight = 200`
    - `int AttackMemory = 250`, ticks an attack stays "recent"
  - `ThreatMemory : ConditionalTrait<ThreatMemoryInfo>, ITick`, with `void Attacked(Actor victim, Actor attacker)` called by the damage reporter (Step 3), plus:
    - `int StrengthNear(CPos cell, int radiusCells)`: summed remembered enemy value in the grid squares overlapping the radius
    - `IEnumerable<(Actor Victim, Actor Attacker, int Tick)> RecentAttacks`: attacks on the owner's actors within `AttackMemory` ticks, newest first, with dead victims dropped
    - `T WeakestTarget<T>(IEnumerable<T> candidates, Func<T, CPos> cellOf, Func<T, int> valueOf, int radiusCells)`: the candidate with the highest `value / (1 + StrengthNear)`, or default when there are none
  - `ThreatMemoryProperties : ScriptPlayerProperties` (Lua, group "Threat"): `int ThreatNear(CPos cell, int radius)`
- An actor's value is its `ValuedInfo.Cost`, 0 if it has none.

- [ ] **Step 1: Write the failing test.** Map `scenario-ai-threat`, 64x48: `cryo-pod` Marines at (6,6) with the marine bot on
  "hard"; xeno `resin-silo` at (58,42); 3 xeno `sentinel` at (30,24) on HoldFire. Script:
  - At tick 50, `Marines.ThreatNear(CPos.New(30,24), 3)` is 0, since the marines have seen nothing.
  - Then it reveals the sentinels by teleporting a marine `rifleman` next to them (HoldFire). At tick 150 `ThreatNear` > 0.
  - Then it moves the rifleman away and kills nothing. `ThreatNear` at tick 150 + 25·k falls below half its peak within
    40 samples (fading works) and stays > 0 for at least the first 5 (memory outlives sight).
  - It prints `TEST ai-threat PASS` only if all three hold.
- [ ] **Step 2:** Run it. Expected: FAIL or a Lua error that `ThreatNear` is unknown.
- [ ] **Step 3: Implement `ThreatMemory`.**
  - Each `Interval`: multiply every square by `FadePercent`, then set each square to max(current, value seen there now).
    Sum over the enemy actors in view, frozen actors included; with `FullVision`, over all enemy actors.
  - For attacks, the bot interface `IBotRespondToAttack` only fires with a bot. Instead, have each owner's actor report damage:
    a small `ReportsThreatOnDamage` actor trait on `^Infantry`, `^Building` and `^Xeno` (whichever bases exist in `units.yaml` and `structures.yaml`) that calls `owner.PlayerActor.TraitOrDefault<ThreatMemory>()?.Attacked(self, attacker)`, implementing `INotifyDamage`. Skip friendly fire.
- [ ] **Step 4:** Run `test_scenarios.sh 150 ai-threat`. Expected: PASS. Also run the whole suite
  (`test_scenarios.sh 150`) and compare its PASS count with a run on the previous commit. Nothing new fails.
- [ ] **Step 5:** Commit: "ThreatMemory: faded grid of seen enemy strength, recent attacks, Lua ThreatNear".

### Task 3: Defend what is attacked

**Files:**
- Modify: `tgmc/code/Bots.cs` (new `DefendBotModule`, next to `MinerGuardBotModule`)
- Modify: `tgmc/rules/ai.yaml` (`DefendBotModule@marines`, `DefendBotModule@xenos`)
- Create: `mod/scenarios/test-ai-defend.lua`, and map entries `scenario-ai-defend`, `scenario-ai-defend-victim-dies`, `scenario-ai-defend-nobody`

**Interfaces:**
- Consumes: `ThreatMemory.RecentAttacks`, `ThreatMemory.StrengthNear`, `MinerGuardBotModule.IsGuard`
- Produces: `DefendBotModule.IsBusy(Actor a) -> bool`
- Info fields:
  - `int Interval = 25`
  - `string[] Protect`, the owner's types worth defending: miners, silos, fields and production buildings
  - `string[] Defenders`, the unit types sent
  - `int OvermatchPercent = 150`: send defenders until their summed value ≥ 150 % of `StrengthNear(victim, 4)`, or until there are no idle units left
  - `int QuietTicks = 200`: release once the victim has gone that long with no attack
- How it works:
  - It implements `IBotTick` and `IBotNotifyIdleBaseUnits`. Units are taken out of the idle list and handed back like `MinerGuardBotModule` does.
  - Each tick it reads `RecentAttacks` for victims of `Protect` types. It skips victims inside the main base radius, which the stock Protection squad covers.
  - It sends defenders by `AttackMove` to the victim's cell, nearest first.

- [ ] **Step 1: Write the failing tests.** One script, three maps, branching on the map title.
  - `ai-defend`: a marine-bot miner on a field at (40,20), the base at (6,20) with 6 idle riflemen, and xeno `hunter` ×2
    spawned at tick 300 beside the miner, attack-moving it. PASS if ≥ 3 riflemen are within 5 cells of the miner by tick 900.
  - `ai-defend-victim-dies`: same map, but the script kills the miner at tick 320. PASS if no exception appears and the riflemen
    are back in the idle pool by tick 1200: they stand within 10 cells of base, or are in a squad.
  - `ai-defend-nobody`: same map, 0 riflemen. PASS if the game reaches tick 900 without an error line.
- [ ] **Step 2:** Run `test_scenarios.sh 150 ai-defend`. Expected: `ai-defend` FAILs, since the stock squad manager ignores
  far victims.
- [ ] **Step 3:** Implement `DefendBotModule` to the interface above. Add the YAML for both factions with each side's fighter
  types.
- [ ] **Step 4:** Run `test_scenarios.sh 150 ai-defend ai-marine-fields ai-retreat ai-medic`. Expected: all PASS.
- [ ] **Step 5:** Commit: "Bots defend any attacked miner, silo or outpost, sized to the attacker".

### Task 4: Raid weak spots

**Files:**
- Modify: `tgmc/code/Bots.cs` (new `RaidBotModule`)
- Modify: `tgmc/rules/ai.yaml` (`RaidBotModule@marines`, `RaidBotModule@xenos`)
- Create: `mod/scenarios/test-ai-raid.lua`, maps `scenario-ai-raid` and `scenario-ai-raid-backoff`

**Interfaces:**
- Consumes: `ThreatMemory.WeakestTarget`, `ThreatMemory.StrengthNear`, `MinerGuardBotModule.IsGuard`, `DefendBotModule.IsBusy`
- Info fields:
  - `int Interval = 100`
  - `string[] Raiders`, fast units: `runner` and `hunter` for xenos, the marine bot's fastest infantry
  - `int Size = 4`
  - `string[] Targets`, enemy economy and outpost types: marine `miner` and `engineer` for the xeno bot, the xeno field and economy actors from `FieldBotModule@xenos` plus `resin-silo` for the marine bot
  - `int MaxThreatPercent = 60`: only targets whose `StrengthNear` is ≤ 60 % of the raid's value
  - `int BackOffPercent = 120`: the raid turns home when `StrengthNear(raid centre, 4)` exceeds 120 % of its remaining value
- Candidates are enemy actors of `Targets` types that are visible now or in the frozen-actor layer.
- **Threat-aware route** (added 2026-11-07 at the user's request, from the influence-map-in-A* idea in the RTS AI guides):
  the raid walks through waypoints from `ThreatMemory.SafePath(CPos from, CPos to) -> List<CPos>`. That is an A* over the coarse
  grid squares, where a step costs 1 + the square's strength / `StepCostValue` (Info field on ThreatMemory, default 100), and the
  result is the cell centres of the squares, with the last one replaced by `to`. Test, in `ai-raid-route`: a sentry wall stands on
  the straight line from silo to miner and an open way goes round it. PASS if no raider comes within 3 cells of a sentry before
  reaching the miner.
- At most one raid is out at a time. Its units go back to the idle list on arrival home, or when all targets near it are dead.

- [ ] **Step 1: Write the failing tests.**
  - `ai-raid`: the xeno bot on "hard" with 6 idle runners at its silo. There are two marine miners equally far away, one with
    3 `sentry-turret` beside it, and both are revealed to the xenos at tick 1 (the script gives the xenos a scout's sight, or
    the map is small enough). PASS if, by tick 1500, xeno runners have come within 4 cells of the bare miner and none within
    6 cells of the guarded one. Also print the guard/raider overlap count (Review Focus 5) and require 0.
  - `ai-raid-backoff`: one bare miner. When a raider comes within 8 cells, the script spawns 4 sentries beside it. PASS if the
    surviving raiders end up nearer their silo than the miner by tick 2000.
- [ ] **Step 2:** Run. Expected: FAIL, since there is no raid yet.
- [ ] **Step 3:** Implement `RaidBotModule` and its YAML.
- [ ] **Step 4:** Run `test_scenarios.sh 150 ai-raid ai-defend ai-marine-fields`. Expected: all PASS.
- [ ] **Step 5:** Commit: "Bots raid the enemy's poorly defended miners and outposts, and back off from walls".

### Task 5: Aim the army at the weakest target

**Files:**
- Modify: `tgmc/code/Bots.cs` (new `AttackTargetBotModule`)
- Modify: `tgmc/rules/ai.yaml` (both factions)
- Create: `mod/scenarios/test-ai-attack-weak.lua`, map `scenario-ai-attack-weak`

**Interfaces:**
- Consumes: `ThreatMemory.WeakestTarget`. Also the stock `SquadManagerBotModule.Squads` (public `List<Squad>`),
  `Squad.Type`, `Squad.IsValid`, `Squad.CenterUnit()`, `Squad.SetActorToTarget((Actor, WVec))`.
- Info fields: `int Interval = 150`, `string[] Targets` (enemy structures worth attacking) and `int OutmatchPercent = 130`.
- Each interval, for each valid `Assault` or `Rush` squad, it sets the target to the `WeakestTarget` among the candidates
  (visible or frozen enemy `Targets`) whose `StrengthNear(cell, 6)` is at most the squad's value × 100 / `OutmatchPercent`
  (added 2026-11-07, from the AoE "attack when stronger" rule in the guides). With no such candidate it leaves the squad alone.
  Test: `ai-attack-weak` also gets a group C with defences worth more than the squad, nearer than A and B; the squad must not go there.

- [ ] **Step 1: Write the failing test.**
  - `ai-attack-weak`: the marine bot, with a squad of 8 riflemen given at start.
  - Two xeno structure groups at equal distance, both revealed: A has 4 defensive xenos on HoldFire, B has none.
  - PASS if the squad's centre comes within 6 cells of B before it comes within 6 cells of A, and there is no exception in the
    log during ticks 0-500 (Review Focus 3).
- [ ] **Step 2:** Run. Expected: FAIL about half the time, since the stock behaviour picks the nearest. Run it 3 times to
  see the failure.
- [ ] **Step 3:** Implement `AttackTargetBotModule` and its YAML.
- [ ] **Step 4:** Run `test_scenarios.sh 150 ai-attack-weak` 3 times. Expected: PASS all 3.
- [ ] **Step 5:** Commit: "Bot armies attack the weakest valuable target they know of".

### Task 6: Measure the balance and record it

**Files:**
- Create: `mod/balance-arms/no-reactive-ai.yaml`, which removes the four new modules and `ThreatMemory` from `Player`:
  `-DefendBotModule@marines:`, `-RaidBotModule@xenos:` and so on
- Modify: `README.md` (bot section: one paragraph on the reactive behaviour) and `PLAN-upgrades.md` "Built so far" if bot balance is mentioned there

- [ ] **Step 1:** Run `OPENRA_DIR=$PWD/build/OpenRA mod/balance.sh 40 400 balance-aivai mod/balance-arms/no-reactive-ai.yaml`.
  Check free memory first: the freqtrade bot fleet shares this box, so keep `BALANCE_JOBS` at its default of 4 or lower.
- [ ] **Step 2:** Run the same with `balance-holdline` and one `aimap-*` map.
- [ ] **Step 3:** Write both win rates with their 95 % intervals into the README paragraph. If an arm shows a stall (median
  match length near the ceiling), say so plainly; that is a finding, not a failure.
- [ ] **Step 4:** Run the full `test_scenarios.sh 150`. Expected: the same PASS set as before Task 2, plus the new tests.
- [ ] **Step 5:** Commit: "Reactive AI: balance before and after, README".
