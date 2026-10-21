# Upgrades tab: plan

Status: first slice built and tested (see "Built so far"). The rest is still plan. Decisions still open are marked OPEN.

## Built so far

- The Upgrade tab: a fourth sidebar button (chevron icon) and the `UpgradeQueue` (`tgmc/code/ProductionQueues.cs`). It is on for marines and SOM by faction, since no building feeds it. Buying creates a hidden actor that provides a prerequisite; `GrantConditionOnPrerequisite` switches units over.
- Two upgrades in `tgmc/rules/upgrades.yaml`: T-12 Rifles (armory, 300) and M412 Rifles (armory and T-12, 500), with TGMC gun item icons. The rifleman now starts with the T-18 carbine and climbs the ladder; the old random rifle is gone.
- Tests: `scenario-upgrade` (buy order, no double buy, and the gun really changes, proven by range gates 8, 9 and 10 cells) passes.
- Also built along the way: the shotgun knockback on full buckshot (`scenario-shotgun-knockback` passes), the rifle-butt melee on weed nodes (`scenario-weed-bash` passes), and the marine bot's weed-node sweep.
- The marine bot buys upgrades: `UpgradeBotModule` (`tgmc/code/Bots.cs`) queues the first buyable upgrade in palette order (rifles, armour, then the other ladders), one at a time, from tick 2500. The Upgrade queue sits ahead of the unit queues in `player.yaml` so it is paid a little each tick even when the units would drain the bank. `scenario-ai-upgrade` passes (both rifle upgrades by about tick 4750).
- The marine bot seeks miners for income: `FieldWorkerBotModule` queues engineers while ore fields lie unclaimed, and `FieldBotModule` already sends them to claim the fields. `scenario-ai-engineers` passes (a bot with no engineer has a marine miner by about tick 300).
- The xeno line: Carapace I (300, evolution-tower), Carapace II (600, maturity-tower and Carapace I), Sharper Claws (300) and Hive Speed (400), through the same Upgrade queue (now on for xenos too; a `faction-xenos` prerequisite hides them from the marines). They are stat multipliers on `^Xeno`: carapace as less damage taken (13 percent each, II also 6 percent slower), claws as 15 percent firepower, hive speed as 12 percent speed. The xeno bot buys them too (`UpgradeBotModule@skirmish`). `scenario-xeno-upgrade` passes: buy order, no double buy, no marine upgrades on offer, and a runner is 74 to 66 ticks over 22 cells after Hive Speed.
- Not measured: the carapace damage cut and the claws bonus have no test of their own (they use the same multiplier pattern as the Rage power). After the carbine start and the new bot modules, two full matches finished with marine wins at ticks 3000 and 5000: the stall is gone, but the xeno AI collapses early. Silo defence for the xeno AI is the next balance step.

## The tab

- A fourth tab beside Infantry, Xeno and Build in the sidebar (`ProductionTypeButton` in `tgmc/chrome/ingame-player.yaml`, group `Upgrade`).
- A new player queue `Upgrade` in `tgmc/rules/player.yaml`, one set for marines and SOM and one for xenos (`Factions`).
- Each upgrade is a small actor with `Buildable`, `Tooltip`, `Valued` and `BuildLimit: 1`. A small queue class (next to `MultiProductionQueue`) does not spawn it. It grants the player a prerequisite instead.
- Units pick the upgraded weapon by condition: `GrantConditionOnPrerequisite` on the unit, `RequiresCondition` on a second `Armament`. No new combat code.
- The AI needs a small bot module, or it never buys an upgrade. OPEN: is that in scope?
- Tests: one Lua scenario that buys an upgrade and checks the new weapon fires, and a lint check that every upgrade has an icon and a description.
- Decided: the tab is always there. Each upgrade unlocks when its building exists, through the normal `Prerequisites:` line on its `Buildable`, so it shows greyed out until then. Losing the building locks it again for new purchases only. An upgrade already bought stays.
- OPEN: which building unlocks which. First guess from the buildings the mod already has:
  - `armory`: rifle, SMG and shotgun ammo (AP, slug, flechette).
  - `ordnance-depot`: SADAR and RPG rounds, grenades.
  - `workshop`: machine gun, minigun and mech weapon upgrades.
  - `evolution-tower` and `maturity-tower`: the xeno upgrades.
  A second tier can need two buildings, or a building plus an earlier upgrade.

## How the mod's guns work today

Read from `tgmc/rules/weapons.yaml`. A weapon fires `Burst` shots `BurstDelays` ticks apart, then waits `ReloadDelay` ticks. One cycle is (Burst - 1) x BurstDelays + ReloadDelay ticks, and damage per cycle is Burst x Damage. Damage per tick is the second divided by the first. Ticks, not seconds, because the game speed changes how long a tick lasts.

| Weapon | Range (cells) | Burst x damage | Cycle (ticks) | Damage per tick |
|---|---|---|---|---|
| TGMCRifle (T-12) | 9 | 3 x 11 | 24 | 1.38 |
| TGMCCarbine (T-18) | 8 | 3 x 7 | 19 | 1.11 |
| TGMCM412 | 10 | 3 x 11 | 32 | 1.03 |
| TGMCSMG | 6.75 | 1 x 5 | 5 | 1.00 |
| TGMCShotgun | 4 | 6 x 6 | 50 | 0.72 (all pellets) |
| TGMCSmartgun | 10.5 | 1 x 7 | 5 | 1.40 |
| TGMCSniper | 12 | 1 x 60 | 40 | 1.50 |
| TGMCMG60 | 10.5 | 1 x 11 | 4 | 2.75 |
| TGMCMinigun | 9 | 8 x 6 | 19 | 2.53 |
| TGMCPlasmaRifle | 9 | 1 x 20 | 22 | 0.91 |
| TGMCSadar | 9 | 1 x 80 (blast) | 90 | 0.89 |
| TGMCMechRPG | 10 | 1 x 90 (blast) | 170 | 0.53 |
| TGMCMechTow | 12 | 1 x 150 | 230 | 0.65 |

So there are three kinds of gun, and upgrades should keep the kinds apart:
- **Fast and light** (SMG, MG60, minigun, carbine): many small hits. Good against swarms, weak against armour, which blocks small damage.
- **Burst rifles** (T-12, M412): the middle. M412 trades fire rate for 1 cell more range.
- **Slow and heavy** (sniper, SADAR, TOW): few big hits. Good against tough xenos and structures, poor against fast runners.

Upgrade rule: an upgrade should move a gun along that trade-off or raise it overall, never only add damage. Examples:
- AP rounds: more damage per shot, slightly slower cycle (T-12 AP, M412 AP).
- Rapid-fire variants: shorter cycle, less damage per shot (T-18 against T-12).
- Incendiary rounds: less direct damage, burn over time.
- Heavy-weapon rounds: SADAR HE for blast, white phosphorus for fire and smoke.

Range is a third axis beside fire rate and damage. Upgrades can change it:
- Mechanism: OpenRA's `RangeMultiplier` trait scales an armament's range by a percent while its `RequiresCondition` holds, so a range upgrade needs no second weapon. A scope, barrel or heavier propellant adds, say, +15% range. A sawn-off or short barrel takes some away for a faster cycle.
- Examples from the table: the rifle (9 cells) against the M412 (10), the sniper (12), the shotgun (4), the SMG (6.75). A range upgrade on the shotgun, say from 4 to 5 cells, makes it a real mid-range gun. The knockback needs a full load of pellets, and pellets scatter more with distance, so a longer shotgun throws less often at its far end.
- Sight limits it. A gun that out-ranges what the unit can see is useless until something spots the target (`TgmcSight` on the unit, `RevealsShroud`). Range upgrades on long guns should come with, or after, a sight upgrade, or the scout role gets stronger by accident.
- Out-ranging matters most against xenos with a ranged attack (sentinel spit, boiler glob) and against structures such as resin turrets. Range upgrades on defences (sentries, mortars, howitzers) are worth considering too.
- The AI keeps using the unit's weapon range for engagement, so it benefits automatically. Check the squad logic, which sets its own distances (`ai.yaml`).

OPEN: the numbers above are the mod's own. The real TGMC stats (fire delay, damage, armour penetration) have not been read, because the local checkout has no gun code. Do we fetch them from the TGMC repo, or tune by feel?

## Effects and models

An upgrade is not only a number. Each one changes how the gun looks and sounds, and special rounds change what the hit does. Every upgrade needs four things: a weapon, a sound, a hit effect and a model.

- **Model in the marine's hands.** `mod/build_sprites.py` builds each unit's body sprite from the TGMC in-hand files (`icons/mob/inhands/guns`, for example `svd_w`, `sadar_100_w`). An upgrade that swaps the gun (T-12 to T-12 AP, SADAR rocket type) needs its own body sprite, picked by the upgrade's condition, the way `WithInfantryBody` is already picked by `gun-ar`, `gun-carbine` and `gun-m412` on the rifleman. The sprite names exist in the TGMC files for most guns in the list.
- **Muzzle and shot.** `MuzzleSequence` and `WithMuzzleOverlay` on the unit, and the weapon's `Projectile` and `Report` sound. Tracer colour and sound should differ per round: AP sharper, incendiary with an orange tracer, slug heavier.
- **Hit effect.** `CreateEffect` warheads on the weapon: the existing `fx-blast`, `fx-light` and spark effects, plus new ones where a round needs its own look.
- **Status effects.** Burning and similar effects need a mechanic, not just a picture. The mod has one already: the flamer's `flame-patch` actor leaves burning ground that hurts what stands in it (`TGMCFlamePatch`), and `ConeDamage` handles the spray. Incendiary and phosphorus rounds reuse it.

### Phosphorus and incendiary rounds, as an example

White phosphorus is burning and dangerous, so it must read that way and behave that way:
- Hit: a bright white-orange burst and smoke, a `flame-patch` that stays on the ground for several seconds, and damage over time to everything inside it, friendly units too.
- Light: the burst lights the ground (the `fx-light` effect), and the smoke hides units standing in it.
- Cost of using it: friendly fire is on, so a marine can burn his own squad. The AI must not fire it at an enemy that stands next to its own units.
- Sound: a hiss and crackle on impact, not the flat HE bang.
- Rocket model: the SADAR WP rocket has its own projectile sprite (`rocket_wp` exists in the TGMC files).
- The same recipe covers incendiary rounds on the M412, M25, SH-410 shells and RPG rounds. They differ in size and duration of the burning patch.

OPEN: who gets the new art? Sprites for the swapped guns come from the TGMC files, but a few effects (WP smoke, tracer colours) have to be drawn or recoloured.

## Armour upgrades (health)

Armour upgrades make a unit tougher. In the mod, toughness is already two separate things, and an upgrade can use either:
- **Health.** `Health: HP` per unit (the marine base is 170, a smartgunner 130, a sniper 110, a Jaeger trooper 140). An upgrade raises it with a `HealthMultiplier` trait that needs the upgrade's condition. It shows straight away on the health bar. A unit already hurt keeps its health ratio.
- **Damage taken.** `DamageMultiplier@armor` (Jaeger medium armour takes 88%, light takes 92%). Several multipliers stack, so an upgrade adds one with `RequiresCondition`. This is better for later tiers, because it makes armour-piercing rounds and xeno claws matter: some units also carry an `Armor: Type` (`HeavyMarine`, `Heavy`, `Light`) that weapons already treat differently through `Versus`.

Principle: everyone starts simple and earns the good kit. A new marine has a basic jumpsuit and a basic rifle. The tab upgrades the whole army step by step up to Jaeger armour. This replaces the separate Jaeger units (scout, skirmisher, trooper, ranger, assault and so on), which are `~disabled` today: the same man now changes armour instead of being a different unit.

The armour sets in the TGMC art (patterns in `mod/build_sprites.py`, `jaeger()`; the SOM has its own light, medium and heavy black sets):
- Basic: marine jumpsuit with a ballistic vest. The start.
- Light Jaeger: scout, skirmisher, trooper patterns. Fast, a little tougher.
- Medium Jaeger: infantry, eva, ranger, helljumper patterns. Takes less from every hit (the 88% multiplier today).
- Heavy Jaeger: gugnir, assault, eod patterns, the "advanced" tier. Slow, `HeavyMarine` armour type, shrugs off claws and acid.

Proposed tiers, to be tuned by feel. Each one changes the body sprite, the health, the damage taken, the speed and the armour type:
1. Light Jaeger: +15% health, faster. Unlocked at the `armory`.
2. Medium Jaeger: more health and 12% less damage taken. Needs light Jaeger and the `ordnance-depot`.
3. Heavy (advanced) Jaeger: more health, 25% less damage taken, `HeavyMarine` armour, slower. Needs medium Jaeger and the `workshop`.

Weapons follow the same idea: basic T-12 and T-18 first, then AP, then the later-tier rifles. Armour tier and weapon tier are separate lines, so a player can go heavy armour first or better guns first.

Xeno equivalent, so both sides have a toughness line: carapace I and II, as extra health and less damage from rifles. Unlocked at the `evolution-tower` and `maturity-tower`. A heavier carapace costs speed.

Model and effect: armour is visible. The TGMC art has the marine jumpsuit with and without armour, and the Jaeger light, medium and heavy suits. Each plating tier swaps the body sprite the same way as a gun upgrade does. A hit on armoured infantry should spark instead of bleed (the mod already has spark and blood effects chosen by target type).

Unit cost: each tier costs requisition per purchase, not per unit. One buy covers the whole army, including units made later.

OPEN: do upgrades apply to units that already exist, or only to units made after the buy? The first is simpler and feels better. Recommend it.

## Smaller roster

Armour upgrades make the Jaeger unit types redundant, so they go. Today the marines have 22 infantry types plus the mech. The Jaeger ones are the same man in different armour:
- Remove: scout, skirmisher, trooper, ranger (all four are `~disabled` already, so nothing can build them today) and assault (`ordnance-depot`). Their health, speed and damage multipliers become the armour tiers above.
- OPEN: heavygunner (450, minigun) and demolitionist (420, demolition charges). They are Jaeger heavy kit, but they carry their own weapon and role. Either keep them as role units, or fold them into weapon upgrades (minigun and demolition charge as machinegunner and rocketeer upgrades). Recommend folding the heavygunner and keeping the demolitionist, who has a unique job.
- Stays: rifleman, medic, engineer, smartgunner, sniper, machinegunner, grenadier, flamer, rocketeer, mortarman, blademan, bomber, squad leader, field commander, mech. The SOM keeps its trooper and veteran.

That leaves about 15 marine types instead of 22.

What removal touches, so nothing is left dangling:
- `tgmc/rules/units.yaml`: the unit blocks. Keep the Jaeger comment's armour numbers as the starting values for the tiers.
- `tgmc/rules/ai.yaml`: `UnitsToBuild` weights, `UnitLimits`, squad `Units:` lists. The AI must also buy armour tiers (see the tab section).
- `tgmc/fluent/tgmc.ftl`: names and descriptions. `README.md`: the unit list and counts.
- `tgmc/code/Bots.cs` and `Events.cs` mention some of these names: check each before deleting.
- `mod/make_placeholders.py` and scenarios `test-jaeger`, `test-heavy`, `test-ai-scout`, `test-explosive`, `test-ai-expand`, `test-nofriendlyfire`, `test-stance-factions`, `test-retreat-factions`, `test-friendly-fire-alert`: swap the removed types for riflemen with the matching upgrade.
- `mod/build_sprites.py`: do NOT delete the Jaeger sprite sheets. The armour tiers use them. Only the per-unit presets for removed units go.
- Saved games and maps: a map that places a removed unit type fails to load. Check the maps in `build/` and the shipped ones.

## Weapon lines that can be upgrades

Names come from the sprite files in the TGMC checkout (`icons/obj/items/guns`), so they are real TGMC guns. Stats are not read yet: the local checkout has no gun code, so numbers must be taken from the TGMC repo before balancing. Tiers below are a first guess from the names.

The mod's current weapon is in brackets.

### Rifles (TGMCRifle, TGMCCarbine, TGMCM412)
- T-12 to T-12 AP (`t12`, `t12_ap`).
- T-18 to T-18 AP (`t18`, `t18_ap`).
- M412 to M412 AP, M412 incendiary, M412E (`m412_ap`, `m412_incend`, `m412e`).
- Later tier: M416 and M416E, T-42, T-81, TX-11, TX-55.
- SOM line: V-31, V-34, V-35, with V-35 AT and V-35 incendiary variants.

### Submachine guns (TGMCSMG)
- M25 to M25 AP, M25 incendiary, M25B2 (`m25`, `m25_ap`, `m25_incend`, `m25b2`).
- T-19, T-90, T-45, MP7, C17, V-21, Skorpion, PPSh.

### Shotguns (TGMCShotgun, TGMCMechShotgun)
- TX-15 to TX-15 slug and TX-15 flechette (`tx15`, `tx15_slug`, `tx15_flech`). This is the natural home of the buckshot / slug choice asked for earlier.
- SH-410 ammo variants: buckshot, ricochet, sabot, tracker, gas.
- T-35, T-39, trenchgun, Mare's Leg, L12, KS-23, double-barrel (`dshotgun`), TS-34.

### Marksman rifles and snipers (TGMCSniper)
- SVD, Mosin, Martini, Garand, L11, SG-153, SG-62, T-37, T-64, ML-12.
- TX-8 to TX-8 impact and TX-8 incendiary rounds.
- TL-127 to TL-127 flak (`tl127`, `tl127_flak`).
- M42C and M42R (`m42r`, `m42r_hvap`, `m42r_smart`).

### Machine guns (TGMCMG60, TGMCMinigun)
- SG-60, T-60, M41A, M412L1, Minimi, RPD, DP-27, C74, L26, V41.
- Minigun and its shotgun variant (`minigun`, `minigun_sg`).
- No smartguns here. The SG-29 and ALF-51B (`sg29`, `alf51b`, mod: TGMCSmartgun) are their own line for the smartgunner, outside the machine-gunner's upgrades.

### Rocket launchers and heavy weapons (TGMCSadar, TGMCMechRPG, TGMCMechTow, TGMCGrenade)
- SADAR with rocket types: AP, HE, white phosphorus (`sadar`, `rocket_ap`, `rocket_he`, `rocket_wp`).
- RPG with rounds: HE, HEAT, incendiary, low-explosive, radiation, thermobaric.
- ICC RPG with rounds: HE, HEAT, low-explosive, thermobaric.
- AT-32 and AT-45 anti-tank launchers.
- C153 with rounds: HE, AT, chemical, incendiary.
- ML-120, T-160, T-26 (with flak and incendiary), T-70, T-72, railgun, pepperball.

### Flamers (TGMCFlamer, TGMCMechFlamer)
- Fuel types as upgrades: standard fuel (orange-red fire, the start), then X-Napalm (blue fire). Blue fire burns hotter: more damage per tick, burns longer, and passes more of a heavy xeno's armour. The cost is a shorter reach or a slower reload, so the choice is not only better.
- The art is already there. `icons/effects/fire.dmi` has red, blue, green, purple and violet fire in three sizes each (`blue_1` to `blue_3` and so on). Today the mod's `flame-patch` uses `red_3` (`mod/build_sprites.py`, "flame-patch"). Blue fire is a second patch: a `flame-patch-blue` sprite from `blue_3`, a hotter `TGMCFlamePatchBlue` weapon, and a blue `fx-light` glow so the ground lights blue.
- The flamer weapon picks the patch actor by condition (`SpawnActor` in `Warhead@3Patch`), as the rifleman picks a gun by condition. The spray (`ConeDamage`) and the muzzle flame also change colour.
- Danger: fire burns friendly units too, and blue fire more so. The AI flamer must hold fire when its own units stand in the patch's reach.
- Other colours (green, purple, violet) are free later tiers or special rounds, such as green for a chemical fuel.

### Energy and plasma (TGMCLaserRifle, TGMCPlasmaRifle)
- TX-73 modes: heat, overcharge, spread.
- Laser series TE: TES, TEX, TER, TEP, TEM, plus Caliver, Charger, Culverin, Tesla.
- Plasma rifle, plasma SMG, plasma cannon.

### Pistols
- A large family (M1911, Deagle, Mateba, T-76, T-44 and more). Probably leave out of the first version.

## How the upgrades go: weapon ladders (current plan)

Decided: an upgrade moves a role to a different weapon, not to a different ammo. Each role climbs a ladder of real TGMC guns. A tier swaps the unit's armament (and its in-hand sprite, sound and muzzle) by condition, the way the rifleman already picks between `gun-ar`, `gun-carbine` and `gun-m412`. Each step has its own stats, so "faster but weaker" or "slower but harder-hitting" is a choice of gun, not a tweak. The ammo upgrades in the earlier table become optional extras; only the signature ones (X-Napalm, phosphorus) are worth keeping.

"In mod" means the weapon already exists in `weapons.yaml`, so the step needs data only. "New" needs a new weapon block and art.

| Role | Step | Gun | In mod | Needs | Cost | What changes against the step before |
|---|---|---|---|---|---|---|
| Rifleman | 0 | T-18 carbine | yes (TGMCCarbine) | start | 0 | light, fast cycle, 7 damage, range 8 |
| Rifleman | 1 | T-12 | yes (TGMCRifle) | armory | 300 | 11 damage, range 9 |
| Rifleman | 2 | M412 | yes (TGMCM412) | armory | 500 | range 10, slower cycle |
| Rifleman | 3 | M416 / TX-55 laser | laser yes (TGMCLaserRifle), M416 new | armory + ordnance-depot | 800 | hard-hitting, long range |
| Rifleman | 4 | Plasma rifle | yes (TGMCPlasmaRifle) | workshop | 1200 | 20 damage per shot, slower |
| SMG (medic, engineer) | 0 to 2 | T-19, then M25, then T-90 | TGMCSMG only | armory | 250 / 400 | higher damage per round, better range |
| Shotgun | 0 | Pump (T-35 or trenchgun) | TGMCShotgun | start | 0 | 6 pellets, slow cycle |
| Shotgun | 1 | TX-15 | new | armory | 400 | faster cycle |
| Shotgun | 2 | SH-410 or double-barrel | new | armory + ordnance-depot | 650 | heavy load, bigger knockback |
| Sniper | 0 | Mosin or Martini | new | start | 0 | slow, 60 damage |
| Sniper | 1 | SVD | new | armory | 450 | faster cycle |
| Sniper | 2 | TX-8 | new | armory + ordnance-depot | 700 | longer range, more damage |
| Sniper | 3 | M42C | new | workshop | 1000 | the heaviest single shot |
| Machine gunner | 0 | M41A | new | start | 0 | steady fire |
| Machine gunner | 1 | SG-60 | yes (TGMCMG60) | workshop | 500 | 4 tick cycle, range 10.5 |
| Machine gunner | 2 | Minigun | yes (TGMCMinigun) | workshop + ordnance-depot | 900 | 8-round bursts, 2.5 damage per tick |
| Rocketeer | 0 | RPG | new | start | 0 | slow, big blast |
| Rocketeer | 1 | SADAR | yes (TGMCSadar) | ordnance-depot | 500 | faster reload |
| Rocketeer | 2 | ICC RPG or AT-45 | new | ordnance-depot + workshop | 900 | anti-armour |
| Flamer | 0 | M240 flamer | yes (TGMCFlamer) | start | 0 | red fire |
| Flamer | 1 | X-Napalm tank | patch + art new | armory + ordnance-depot | 600 | blue fire, hotter, longer burn |
| Armour (everyone) | 1 | Light Jaeger | sprites exist | armory | 300 | +15% health, faster |
| Armour (everyone) | 2 | Medium Jaeger | sprites exist | armory + ordnance-depot | 600 | 12% less damage |
| Armour (everyone) | 3 | Heavy (advanced) Jaeger | sprites exist | workshop | 1000 | 25% less damage, slower |
| Xenos | 1 to 3 | Carapace, claws, speed | stats only | evolution-tower, maturity-tower | 300 to 600 | not guns: needs its own design |

Smartguns are left out of the machine gunner's ladder, as decided. The smartgunner has his own gun and no ladder yet. OPEN: should he get one (SG-29, then ALF-51B)?

Cheapest order to build: the rifleman ladder (4 of 5 steps are data only), the machine gun and rocket steps that exist, and the three armour tiers. The other ladders need new weapon blocks and in-hand sprites from `mod/build_sprites.py`.

## Extras, last: AP and flaming rounds

Do not forget these. They come after the weapon ladders and armour are working, as a second layer on top of a gun the player already has, so they sit at the end of the build order and the end of each ladder:
- **AP rounds.** More damage against armoured targets, a little less against soft ones, often a slightly slower cycle. Reuses the `Versus` armour table that claws and acid already use. Needs the armory. Candidates: T-12 AP, T-18 AP, M412 AP, M25 AP, machine gun AP belt, HVAP for snipers.
- **Flaming (incendiary) rounds.** Less direct damage, plus a small burning patch on the target that burns for a few seconds, reusing the flamer's `flame-patch`. Needs the armory and the ordnance-depot. Candidates: M412 incendiary, M25 incendiary, SH-410 shells, RPG incendiary. The strongest forms are the signature ones: X-Napalm for the flamer (blue fire) and phosphorus rockets for the SADAR (burning, smoke, burns friendlies).
- AP and flaming are exclusive per gun: one or the other, chosen when bought, so the choice means something. A player cannot have both on the same weapon.
- Both need their own look: AP gets a sharper tracer and a brighter hit spark, flaming gets an orange tracer and fire where it lands.
- The full list of ammo variants that exist in the art is in the earlier table below and in the weapon lines section.

## Seeing the progress

The player should see the army grow, not read it off a list. Four places:
- **On the units.** Each step swaps the in-hand gun sprite on every unit of that role at once, existing units included, with a short flash and a sound when the upgrade lands. A squad with M412s looks different from one with carbines, and a heavy Jaeger looks different from a basic marine. Armour and gun together make the tier readable at a glance from the map.
- **In the tab.** Each ladder is a row of icons, one per step. Bought steps are lit, the next one is highlighted with its cost, later ones are dimmed, and a step whose building is missing shows which building it needs (the same greyed-out rule as units and structures). Hovering a step shows the gun's numbers against the one it replaces: damage, cycle, range.
- **On the selection card.** `SelectionReadoutLogic` already shows the selected unit. It would also show the gun's name and its step (for example "M412, step 2 of 4"), plus the armour tier.
- **In the event log and end screen.** `TgmcEventLog` records each purchase, and the end-of-match stats list the tiers each side reached. That makes a long match readable afterwards, and it is how we will see whether the AI buys upgrades in the balance runs.

OPEN: icons for the steps. The TGMC art has the in-hand sprites but not the item icons at the right size, so the ladder icons are either the hand sprite cropped, or the `icons/obj/items/guns` item sprites scaled down. Recommend the item sprites.

## Earlier table (ammo-based, superseded)

Every number is a first guess to tune by feel. A cost is requisition per purchase, paid once for the whole army.

| Line | Tier | Upgrade | Needs (building / earlier upgrade) | Cost | Effect | Look |
|---|---|---|---|---|---|---|
| Armour | 1 | Light Jaeger | armory | 300 | +15% health, faster | light Jaeger chest and helmet |
| Armour | 2 | Medium Jaeger | armory + ordnance-depot / Light Jaeger | 600 | +15% more health, 12% less damage taken | medium Jaeger sprite |
| Armour | 3 | Heavy (advanced) Jaeger | workshop / Medium Jaeger | 1000 | more health, 25% less damage, `HeavyMarine` armour, slower | heavy Jaeger sprite |
| Rifles | 1 | AP rounds (T-12, T-18, M412) | armory | 300 | more damage per shot, cycle about 10% slower | sharper tracer, AP gun sprite |
| Rifles | 2 | Optics | armory / AP rounds | 400 | +10% range, +1 sight | scope on the gun |
| Rifles | 3 | Incendiary rounds (M412) | armory + ordnance-depot / AP rounds | 600 | less direct damage, small burning patch | orange tracer, small fire on hit |
| SMGs | 1 | M25 AP | armory | 250 | more damage per shot | AP gun sprite |
| Shotguns | 1 | Slug rounds | armory | 300 | one heavy pellet, longer range, no spread, no knockback | slug sound and tracer |
| Shotguns | 1 | Flechette rounds | armory | 300 | pellets pierce armour, less damage to soft targets | thin tracers |
| Shotguns | 2 | Choke | armory / either shell | 400 | +1 cell range, tighter spread | longer barrel sprite |
| Snipers | 1 | HVAP rounds | armory | 400 | more damage per shot, +range | brighter tracer |
| Machine guns | 1 | Heavy barrel | workshop | 500 | +15% range, more damage per round, slower to start | longer barrel sprite |
| Machine guns | 2 | AP belt | workshop / Heavy barrel | 600 | armour-piercing hits | tracer colour |
| Flamers | 1 | X-Napalm | armory + ordnance-depot | 600 | blue fire: hotter, burns longer, passes armour, shorter reach | blue fire, blue ground glow |
| Rockets | 1 | HE rockets (SADAR, RPG) | ordnance-depot | 400 | bigger blast | HE rocket sprite |
| Rockets | 2 | Phosphorus rounds | ordnance-depot + armory / HE rockets | 700 | fire patch, damage over time, burns friendlies, smoke | WP rocket, white-orange burst, smoke |
| Defences | 1 | Long-range sentries | workshop | 500 | +range on sentries, mortars, howitzers | none, or a scope |
| Xenos | 1 | Carapace I | evolution-tower | 300 | +15% health | thicker plates on the sprite |
| Xenos | 2 | Carapace II | maturity-tower / Carapace I | 600 | less damage from rifles, slightly slower | heavier plates |
| Xenos | 1 | Sharper claws | evolution-tower | 300 | more claw damage | none |
| Xenos | 1 | Hive speed | evolution-tower | 400 | faster movement | none |

The XENO rows need design before building: the gun list does not apply to them.

## More ideas (parked, none decided)

Recommended to take first: veterancy, economy upgrades, research time and risk. The rest wait.

1. **Veterancy.** Individual units level up from kills, on top of the army-wide upgrades. OpenRA has `GainsExperience` built in. It rewards keeping units alive and fits the selection card.
2. **Economy upgrades.** Miner output and miner health, tied to the miners (`MinerField`, `CashTrickler`). Gives the fight over the miners a reason beyond the cash.
3. **Support upgrades.** Medic heal speed, engineer repair and build speed, and shorter cooldowns on drop pod and orbital strikes.
4. **Forks.** At some tiers the player picks one of two paths, such as heavy armour (slow, tough) or light armour (fast, fragile). The AP or flaming choice is the same idea. Builds then differ between matches.
5. **Faction identity.** The SOM gets its own V-series ladder (V-31, V-34, V-35) and its black armour sets, so the two human factions do not play alike.
6. **Research time and risk.** An upgrade takes time to research. If the unlocking building dies mid-research, progress pauses. Raiding the armory then has a point.
7. **Xeno counter-play.** Xeno upgrades react to what the marines bought: more AP rounds on the marine side makes the carapace line worth more. The AI could choose from this.
8. **Defence upgrades.** Sentries, cades and resin turrets get their own small tiers.
9. **Data-driven tuning.** Keep every upgrade's cost and numbers in one table file, not spread across the rules files, so balancing is one edit.
10. **Upgrade balance harness.** Run matches with and without a given upgrade through `mod/balance.sh` and compare win rates. That is the proof an upgrade is worth its cost.

## Suggested first version

Three upgrades per side, so the tab, queue and AI hook can be proven before filling it with many guns.
- Marines: T-12 AP rounds, TX-15 slug and flechette shells, SADAR HE and white phosphorus rounds.
- Xenos: thicker carapace, sharper claws, faster movement. These are not guns, so the list above does not apply to them. OPEN: which xeno upgrades.
