# Reactive AI and the Evac mission: design

Status: agreed in conversation on 2026-11-07. Two linked parts, built in this order: Part A (the AI reacts to the player),
then Part B (a defence mission that uses it).

## Why

The bots play their own game and barely notice the player. The user wants the AI to respond to what the player does, the way
Age of Empires AI does: it remembers what it has seen, defends what is being hit, and goes for the player's weak spots. The
user also wants a defence mission: marines build up a base under xeno waves and must get out on an evac shuttle at the end.

## Part A: the AI reacts to the player

### A1. Threat memory (the base everything else reads)

A per-player memory of where enemy strength has been seen, on a coarse grid over the map (cell size is the builder's call).

- Each cell holds the known enemy strength there: the value of enemy units and defensive structures seen in it (cost, from
  `Valued`, is a fair first measure; the builder may weight turrets and cades higher).
- What is seen updates the cell. What is no longer seen fades over time, like `CounterPickBotModule`'s remembered sightings do
  now. Fog is respected: the AI only knows what it saw. Scouting (`ScoutBotModule`) feeds it.
- It also records the AI's own assets that are under attack (from damage notifications), with the attacker's strength.
- Other modules ask it simple questions: "how strong is the enemy around here", "which of these targets is weakest",
  "which of my things is under attack right now".

### A2. Responses that read it

- **Defend what is attacked.** When any of the bot's assets is hit (a miner, a silo, a field, an outlying building, not just
  the main base), it sends a force sized to beat the remembered attacker strength there. The force goes back to its squad when
  the attack ends. The uncommitted `MinerGuardBotModule` (two fighters standing at each marine miner) already does part of
  this; it is finished and tested first, then the new response builds on it or replaces it, whichever is simpler.
- **Raid the player's weak spots.** The bot sends small, fast raiding groups at enemy assets the memory rates as poorly
  defended: lone miners, outlying fields, structures with few turrets nearby. A raid backs off when it meets more than it can
  beat (the existing `RetreatBotModule` handles single wounded units; this is the group turning back).
- **Attack where it is weak.** The main squad's attack target is chosen by the memory too: the enemy asset with the best
  value-to-defence ratio, instead of the stock "nearest enemy base" choice.
- Both factions get it: the marine bot and the xeno bot. It reacts to any enemy, human or bot, so bot-vs-bot balance runs
  exercise it too. (Builder's call, agreed in review.)
- `FieldDefenseBotModule` (sentry turrets built beside each marine miner) stays as it is: it places structures, the defend
  response moves units, so they do not fight over the same actors.

### A3. How we know it worked

- A scenario test per response: a bot's miner is attacked and defenders arrive; an undefended player miner gets raided while a
  defended one is left alone; a raid that meets a turret wall turns back.
- Bot-vs-bot runs on the balance harness (commit `9e074cc`) before and after, so a change shows up as a win-rate shift with its
  confidence interval, not a feeling. Any shift is acceptable once it is measured and reported; it is not a gate that blocks
  a response from shipping. (Builder's call.)

## Part B: the Evac mission

### What the player does

One map, about 10 minutes from start to the shuttle leaving.

1. The marines start with a small base, like Hold the Line.
2. Xenos attack in waves. Between waves the player builds cades, sentries and other defences, and trains marines and mechs,
   as in skirmish.
3. Money comes from holding miners on ore fields, plus a payout after each wave survived. Fields outside the walls pay but are
   exposed, so holding them is a risk the player chooses.
4. Near the end the evac shuttle lands at a landing zone away from the base. From then on the xenos come continuously, not
   in waves.
5. The player gets marines from the base to the landing zone and onto the shuttle while the xenos pour in. When the shuttle
   leaves, the mission is won if at least one marine is on board. Mechs, turrets and buildings stay behind.
   - The shuttle waits about 90 seconds after landing, with a countdown on screen, then takes off on its own.
   - The player can launch it early with an order once they judge enough marines are aboard.
   - No seat limit: every marine that reaches it can board. (All three agreed with the user.)
6. The mission is lost if the shuttle leaves empty, or if every marine is dead and the player can no longer train one.
   Production keeps working during the evac, so a fresh recruit sprinting to the shuttle is a valid last hope. (Builder's
   call.)

### Waves

- **Varied.** No two waves the same: they change in size, xeno castes and the direction they come from. The difficulty grows
  over the 10 minutes and ends in the continuous assault at evac.
- **The split agreed with the user:** the mission script decides *when* and *how much* (timing, size and caste mix of each
  wave, so the pacing stays fair). The xeno side decides *where*: each wave is aimed at the player's weak points (the side
  with the fewest sentries, an unguarded miner, a gap in the cades), using the threat memory from Part A.
- The waves are not fair-fog: the mission xenos may know the whole marine base. Builder's call whether they read the A1
  memory with full vision or score targets directly; either way the targeting rule is the same as the skirmish raid rule.

### Fits the existing code

- The four survival maps (Hold the Line, Night Raid, Last Stand, The Hundred) already run timed waves from
  `mod/scenarios/wave-survival.lua`, with per-mission tables in `mission-*.lua` and maps written by
  `mod/make_placeholders.py`. Evac extends this rather than starting over; `wave-survival.lua` should keep working for the
  other four.
- Hold the Line has no ore fields and there is no shuttle actor yet. Both are new: fields use the existing `miner-field`
  actor; the shuttle is a new actor that lands, takes marines aboard and takes off. OpenRA's `Cargo`/`Passenger` traits are
  the obvious start.
- The mission shows the time to evac and the next wave on screen, and plays the existing wave and distress notifications.

### How we know it worked

- Scenario tests in the existing headless style: a wave targets the weakest side, the per-wave payout arrives, the shuttle
  lands and boards marines, one marine aboard wins, no marines loses.
- A play-through by the user decides whether 10 minutes and the wave sizes feel right. The numbers are a first guess and will
  be tuned.

## Goals

- The bots visibly react to the player: defend what is hit, punish undefended assets.
- One Evac mission that is fun for 10 minutes and ends in a frantic run to the shuttle.

## Non-goals (for now)

- Bot personalities (rusher, turtler) and difficulty levels. They come after this, as YAML settings on these same modules.
- An LLM commander.
- More than one Evac map.
- Sound: there is no ffmpeg on this box, so sounds stay unbuilt and untested.

## Anti-goals

- An AI that cheats in skirmish: it must only know what it saw (the mission xenos are the stated exception).
- Waves that feel the same every time, or that ignore how the player built the base.
- Breaking the four existing survival maps or the current skirmish bots' win rates without knowing it.

## Left to the builder

- Grid size, fade rate, value weights and every tuning number.
- Whether A1 is a player trait read by bot modules or a bot module itself, and how Lua reaches it.
- The map layout for Evac, where the landing zone and fields go, and the shuttle's art.
- Whether `MinerGuardBotModule` stays as-is under the new defend response or is folded into it.
