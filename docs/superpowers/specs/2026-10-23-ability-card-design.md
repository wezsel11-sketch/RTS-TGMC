# Ability card and unit ability kits — design

Date: 2026-10-23. Status: draft for approval.

## Intent

Selecting a unit should show what that unit can do, Warcraft 3 style: a grid of buttons with hotkeys, cooldowns and tooltips,
and every unit should have at least one ability of its own. The user's examples: the Squad Leader / Field Commander get a
Rally that boosts the marines around them, the mech gets its rocket launcher, the mortar and artillery get different shells.
The user wants everything TGMC has added now and tuned later in play ("once gaming we can check if it's good enough or need more").

## Goals

- One command card (layout A, chosen by the user from the mockup) that replaces today's card.
- Every buildable unit on all three sides gets at least one ability, taken from what TGMC itself gives that unit or caste.
- Abilities can be aimed by clicking (ground or unit), and can be toggles (ammo/shell type, cloak), not only fire-and-forget.
- The AI (AbilityBotModule) keeps using abilities, including the new aimed ones.

## Non-goals

- Balance. Numbers are first guesses; the user will tune them after playing.
- New art. Buttons show text labels, as today's card does; icons are a later pass.
- TGMC abilities that need systems the mod does not have (listed under "Left out").

## Anti-goals

- Today's buttons must not get lost: stop, attack-move, patrol, stances, retreat, evolve/devolve, medic, infected all stay
  reachable from the new card.
- No ability may break the existing scenario tests (`mod/scenarios`).

## The card (layout A)

- Replaces `Background@COMMAND_CARD` in `tgmc/chrome/ingame-player.yaml` and `CommandCardLogic` in `tgmc/code/Events.cs`,
  same screen spot. A 4 x 3 grid of square buttons.
- Row 1, fixed: Attack (attack-move), Stop, Patrol, Stance (one button that cycles Aggressive / Guard / Return fire / Hold fire,
  label shows the current stance).
- Rows 2-3: up to 8 slots for the selected unit's abilities, in slot order. The side-specific buttons (Evolve, Devolve,
  Retreat, Medic, Infected) take ability slots on the units they apply to, after the unit's own abilities. Medic and
  Infected show only while someone in the selection is hurt or infected; if a unit still has more than 8, the last ones are
  hidden and keep their hotkeys (my call).
- Each button: hotkey letter top-left, charges bottom-right, a dark shadow while cooling down, a gold border while active
  (buff running or toggle on). Hover tooltip: name, one-line description, cooldown.
- Hotkeys by slot: R T E G / X J K L (rebindable in hotkeys.yaml). Q W Z C B are OpenRA's own keys (select all, select type,
  sell, repair, beacon) and V is Retreat, so the Warcraft layout was not used. Keys show in the button tooltip, not on the button
  (the user asked for a compact card).
- Mixed selection: the card shows the abilities of the unit type with the most units selected (my call; WC3 uses a sub-group
  tab key, which we can add later). Pressing a button makes every selected unit of that type that has the ability ready use it.
- `ActiveAbilityInfo.Slot` goes from 1-2 to 1-8.

## New ability mechanics (ActiveAbility in tgmc/code/CasteAbilities.cs)

1. Aimed abilities: new `Aim: Target` (pick a ground cell) and `Aim: TargetActor` (pick a unit). Pressing the button
   enters a targeting cursor (an OrderGenerator, like attack-move does); a click inside `Range` uses it, out of range the unit
   walks into range first, right-click cancels. The AI aims at the densest enemy group in `AiRange`.
2. Toggles: `Toggle: true` makes the button switch `Condition` on and off instead of timing it. A `Group` name makes toggles
   exclusive (picking HE switches off Incendiary). Shell and rocket types become armaments gated by these conditions,
   the same way the mech presets already gate theirs.
3. Auras: `AuraRange` + `AuraCondition` grant a timed condition to friendly units in range (leader orders, queen screeches,
   drone salve). Uses OpenRA's external conditions, as the gas/stun effects already do.
4. Dash/charge: `ChargeDistance` moves the unit in a straight line to the target cell, hitting what it meets with `Weapon`
   (mech Overboost, bull charges, hunter Pounce, warrior Lunge, runner Evasion dash). Reuses the Thrown movement from
   `Knockback.cs`.

## Unit kits (from TGMC, simplified to the mechanics above)

Marines:
- Squad Leader: Move order (Rally: speed aura), Hold order (damage-reduction aura), Focus order (accuracy aura), plus today's
  Smoke, Mirage, Mark.
- Field Commander: Move, Hold, Focus orders (bigger range than the SL), Mark.
- Mech: Overboost (dash), Assault Armor (burst around it), Cloak (toggle), Pulse Armor (short damage shield), Leg Overload
  (toggle: faster, loses health over time), Smoke, Rocket Barrage (aimed, the rocket pod on command).
- Mortarman and mortar emplacement: shell toggle HE / Incendiary / Smoke / Plasma-drain, Flare (aimed: reveals an area).
- Artillery emplacement: shell toggle HE / Incendiary / White phosphorus / Plasma-drain.
- Rocketeer: rocket toggle HEAT / Anti-armour (AP) / White phosphorus / Smoke.
- Rifleman: Frag grenade (aimed). Grenadier: grenade toggle Frag / Incendiary / Smoke.
- Medic: Stim (speed + heal aura, short). Engineer: Build Cade (spawn a cade at the clicked cell).
- Sniper: Aimed Shot (aimed at a unit, heavy hit, long cooldown). Smartgunner: Overdrive (fire-rate buff, then slows).
- Machinegunner / heavygunner: Deploy (toggle: no moving, more range and fire rate). Flamer: Wall of Fire (aimed line).
- Blademan: Lunge (dash). Skirmisher: Sprint. Demolitionist: Plant Charge (aimed at a structure). Synth: Repair Burst.
- Bomber: Detonate (as today).

SOM: each SOM unit gets the kit of its marine counterpart; the SOM rocketeer's toggle is HEAT / Thermobaric / Radiation;
SOM mech = mech; SOM scout gets Cloak; SOM veteran gets Sprint.

Xenos (castes that have nothing get their TGMC set; castes with abilities get the missing TGMC ones):
- Runner: Evasion (dodge), Pounce (dash), Acidic Missile (aimed).
- Hunter: Stealth (toggle), Pounce (dash), Hunter's Mark (aimed at a unit), Silence (aimed: stops abilities in an area).
- Drone: Acidic Salve (heal a xeno, aimed at a unit), Enhancement (buff a xeno), Plant Weed Node (spawn).
- Boiler: Bombard (aimed, long range), bombard toggle Acid / Neuro gas, Acid Shroud (smoke around it).
- Bull: Plow Charge (knocks aside), Headbutt Charge (throws back), Gore Charge (damage) - all dashes.
- Sentinel: + Toxic Grenade (aimed). Warrior: + Lunge, Agility (speed toggle). Spitter: + Acid Grenade (aimed), Acid Mine.
- Queen: + Heal (aimed at a xeno), Give Plasma (aimed at a xeno), Healing Screech, Frenzy Screech (auras).
- Facehugger: Leap (dash onto a marine). Others keep what they have.

## Effects (user: "give these abilities the right effect. Like SL/FC command is like a yell")

Every ability gets a fitting sound and visual, built from what the mod already has (Sounds/EffectImage on ActiveAbility,
floating text, ExplosionParticles, MuzzleGlow, the hit flash, TGMC's sound and effect sheets):
- Leader orders: a shouted voice line from the leader, the order word over their head ("MOVE!", "HOLD!", "FOCUS!") and a
  ring that spreads to the aura's edge; buffed marines show a small marker while the buff lasts.
- Screeches and xeno auras: the screech sound and a coloured ring; the heal ones tint the healed xenos green.
- Dashes/charges: dust (and sparks for the mech) along the path, an impact sound on hit.
- Shell/rocket toggles: the click of a loading sound; each shell type has its own impact (fire for incendiary, white smoke
  for WP and smoke, purple for plasma-drain, light for flare).
- Cloak/stealth: the unit fades to near-invisible for its owner and fully for the enemy, with TGMC's cloak on/off sounds.
- Buffs (Overdrive, Stim, Pulse Armor, Agility, Leg Overload): a tint or glow on the unit while active.
Where TGMC has the sound or sprite, use TGMC's; otherwise reuse the closest one the mod already ships.

## Left out (no system for it in the mod)

Hive Message, Watch Xenomorph, Zoom, Long Range Sight, Toggle Lights, Internals, Seat swap, Essence Link, Disguise,
Psychic Trace, Choose Xeno Leaders, the mech's Reload/Repairpack (mechs have no ammo/parts in the mod).

## Constraints

- OpenRA engine (bleed, build/OpenRA), mod code in tgmc/code, rules in tgmc/rules. Lua 5.1 for scenarios.
- Headless scenario tests (mod/scenarios, run_scn.sh) are the test harness; each new mechanic gets one scenario.
- `--check-yaml` must stay at 0 errors.

## Order of work

1. The card (layout A) on today's 25 abilities; old scenarios still pass.
2. The four mechanics (aim, toggle, aura, dash), one scenario each.
3. Kits: marines, then xenos, then SOM. Each batch rebuilt, linted, and one scenario per new mechanic use.

## Left to the builder

Exact numbers (ranges, cooldowns, damage), tooltip wording, which weapon each ability reuses or the new weapons it needs,
the order of abilities within a unit's slots.
