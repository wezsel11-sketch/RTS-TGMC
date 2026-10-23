#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System;
using System.Collections.Immutable;
using System.Linq;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

// Extra modules for the skirmish AI. The engine's own modules build the base, train a fixed mix and send squads out; these add what a
// player would do on top: pick units to counter what the enemy fields, evolve, bring medics to the wounded, pull wounded units back
// and scout the map. Each one is switched on by a condition in ai.yaml, so the difficulty levels can leave some of them out.
namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("One counter: when the enemy fields many of Enemies, the AI wants more of Units.")]
	public class CounterRule
	{
		[Desc("Enemy unit types this rule reacts to.")]
		public readonly string[] Enemies = [];

		[Desc("Own unit types that counter them.")]
		public readonly string[] Units = [];

		[Desc("How much the want for these units grows when every enemy seen is of the Enemies types (scaled down by their share).")]
		public readonly int Bonus = 100;

		public CounterRule(MiniYaml yaml) { FieldLoader.Load(this, yaml); }
	}

	[TraitLocation(SystemActors.Player)]
	[Desc("Looks at what the enemy has been seen to field and asks the unit builder for units that counter it.")]
	public class CounterPickBotModuleInfo : ConditionalTraitInfo
	{
		[Desc("Ticks between looks at the enemy.")]
		public readonly int Interval = 150;

		[Desc("Does nothing while cash is below this.")]
		public readonly int MinCash = 150;

		[Desc("Enemy units that must have been seen before the AI reacts.")]
		public readonly int MinSeen = 4;

		[Desc("Open requests for one unit type before it stops asking for more.")]
		public readonly int MaxPending = 2;

		[Desc("Most units of one type the AI keeps through counter-picking.")]
		public readonly int MaxOwned = 8;

		[Desc("How much of what was seen is remembered each look (percent), so an old sighting fades.")]
		public readonly int MemoryPercent = 96;

		[FieldLoader.LoadUsing(nameof(LoadCounters))]
		public readonly ImmutableArray<CounterRule> Counters = [];

		static object LoadCounters(MiniYaml yaml)
		{
			var counters = yaml.NodeWithKeyOrDefault("Counters");
			return counters == null ? [] : counters.Value.Nodes.Select(n => new CounterRule(n.Value)).ToImmutableArray();
		}

		public override object Create(ActorInitializer init) { return new CounterPickBotModule(init.Self, this); }
	}

	public class CounterPickBotModule : ConditionalTrait<CounterPickBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		readonly Dictionary<string, float> seen = [];
		int countdown;

		public CounterPickBotModule(Actor self, CounterPickBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;

			foreach (var key in seen.Keys.ToList())
				seen[key] = seen[key] * Info.MemoryPercent / 100f;

			var now = new Dictionary<string, int>();
			foreach (var a in world.Actors)
			{
				if (a.IsDead || !a.IsInWorld || a.Owner == player || player.RelationshipWith(a.Owner) != PlayerRelationship.Enemy || !a.CanBeViewedByPlayer(player))
					continue;

				now[a.Info.Name] = now.GetValueOrDefault(a.Info.Name) + 1;
			}

			foreach (var (name, count) in now)
				seen[name] = System.Math.Max(seen.GetValueOrDefault(name), count);

			var total = seen.Values.Sum();
			if (total < Info.MinSeen || player.PlayerActor.Trait<PlayerResources>().GetCashAndResources() < Info.MinCash)
				return;

			var buildable = AIUtils.FindQueuesByCategory(player).SelectMany(g => g).SelectMany(q => q.BuildableItems()).Select(i => i.Name).ToHashSet();
			var mine = world.Actors.Where(a => a.Owner == player && !a.IsDead && a.IsInWorld).GroupBy(a => a.Info.Name).ToDictionary(g => g.Key, g => g.Count());
			var requesters = player.PlayerActor.TraitsImplementing<IBotRequestUnitProduction>().ToArray();

			var score = new Dictionary<string, float>();
			foreach (var rule in Info.Counters)
			{
				var share = rule.Enemies.Sum(e => seen.GetValueOrDefault(e)) / total;
				if (share <= 0)
					continue;

				foreach (var unit in rule.Units)
					score[unit] = score.GetValueOrDefault(unit) + rule.Bonus * share;
			}

			var best = score.Where(kv => buildable.Contains(kv.Key) && mine.GetValueOrDefault(kv.Key) < Info.MaxOwned
					&& requesters.Sum(r => r.RequestedProductionCount(bot, kv.Key)) < Info.MaxPending)
				.OrderByDescending(kv => kv.Value).Select(kv => kv.Key).FirstOrDefault();

			if (best != null)
				foreach (var r in requesters)
					r.RequestUnitProduction(bot, best);
		}
	}

	[TraitLocation(SystemActors.Player)]
	[Desc("Evolves the AI's units into their next caste when there is cash to spare.")]
	public class EvolveBotModuleInfo : ConditionalTraitInfo
	{
		[Desc("Ticks between looks at the army.")]
		public readonly int Interval = 100;

		[Desc("Cash that must remain after the evolve, so it does not starve unit production.")]
		public readonly int CashReserve = 200;

		[Desc("Evolves at most this many units per look.")]
		public readonly int MaxPerLook = 2;

		[Desc("Only units above this share of their health evolve (a hurt unit would stay hurt).")]
		public readonly int MinHealthPercent = 60;

		[Desc("Castes that stay as they are (workers, larvae and the queen).")]
		public readonly string[] Keep = [];

		public override object Create(ActorInitializer init) { return new EvolveBotModule(init.Self, this); }
	}

	public class EvolveBotModule : ConditionalTrait<EvolveBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public EvolveBotModule(Actor self, EvolveBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var ordered = 0;
			foreach (var pair in world.ActorsWithTrait<Evolves>().Where(x => x.Actor.Owner == player).Shuffle(world.LocalRandom))
			{
				var actor = pair.Actor;
				var evolves = pair.Trait;
				if (ordered >= Info.MaxPerLook)
					break;

				if (actor.IsDead || !actor.IsInWorld || Info.Keep.Contains(actor.Info.Name))
					continue;

				var health = actor.TraitOrDefault<IHealth>();
				if (health != null && health.HP * 100 < health.MaxHP * Info.MinHealthPercent)
					continue;

				if (!evolves.CanEvolve(actor, Info.CashReserve))
					continue;

				bot.QueueOrder(new Order("Evolve", actor, false));
				ordered++;
			}
		}
	}

	[TraitLocation(SystemActors.Player)]
	[Desc("Sends medics to the wounded and infected, and otherwise keeps them close to the fighting units.")]
	public class MedicBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 40;

		[Desc("Unit types that act as medics.")]
		public readonly string[] Medics = [];

		[Desc("Units below this share of their health count as wounded.")]
		public readonly int WoundedPercent = 75;

		public override object Create(ActorInitializer init) { return new MedicBotModule(init.Self, this); }
	}

	public class MedicBotModule : ConditionalTrait<MedicBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public MedicBotModule(Actor self, MedicBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		bool Needs(Actor a)
		{
			if (a.TraitOrDefault<Infestable>() is { IsInfected: true })
				return true;

			var health = a.TraitOrDefault<IHealth>();
			return health != null && health.HP * 100 < health.MaxHP * Info.WoundedPercent;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var own = world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.Info.HasTraitInfo<MobileInfo>()).ToList();
			var medics = own.Where(a => Info.Medics.Contains(a.Info.Name) && a.IsIdle).ToList();
			if (medics.Count == 0)
				return;

			var patients = own.Where(a => !Info.Medics.Contains(a.Info.Name) && a.Info.HasTraitInfo<InfestableInfo>() && Needs(a)).ToList();
			var soldiers = own.Where(a => !Info.Medics.Contains(a.Info.Name) && !a.IsIdle && a.Info.HasTraitInfo<AttackBaseInfo>()).ToList();

			foreach (var medic in medics)
			{
				Actor goal = null;
				if (patients.Count > 0)
				{
					goal = patients.MinBy(p => (p.CenterPosition - medic.CenterPosition).LengthSquared);
					patients.Remove(goal);
				}
				else if (soldiers.Count > 0)
				{
					// No one to heal: stay with the fighting units, so help is near when they are hit.
					goal = soldiers.MinBy(s => (s.CenterPosition - medic.CenterPosition).LengthSquared);
					if ((goal.CenterPosition - medic.CenterPosition).HorizontalLengthSquared < 6 * 6 * 1024 * 1024)
						continue;
				}

				if (goal != null)
					bot.QueueOrder(new Order("Move", medic, Target.FromCell(world, goal.Location), false));
			}
		}
	}

	[TraitLocation(SystemActors.Player)]
	[Desc("Pulls badly wounded units back to a refuge (a medbay, a medic or the hive) and lets them return when mended.")]
	public class RetreatBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 20;

		[Desc("A unit below this share of its health retreats.")]
		public readonly int RetreatPercent = 30;

		[Desc("A retreating unit is free to fight again above this share.")]
		public readonly int ReturnPercent = 75;

		[Desc("Actor types that count as a refuge.")]
		public readonly string[] Refuges = [];

		[Desc("Unit types that never retreat.")]
		public readonly string[] Exclude = [];

		public override object Create(ActorInitializer init) { return new RetreatBotModule(init.Self, this); }
	}

	public class RetreatBotModule : ConditionalTrait<RetreatBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		readonly HashSet<uint> retreating = [];
		int countdown;

		public RetreatBotModule(Actor self, RetreatBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var refuges = world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && Info.Refuges.Contains(a.Info.Name)).ToList();
			if (refuges.Count == 0)
				return;

			foreach (var unit in world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.Info.HasTraitInfo<MobileInfo>() && !Info.Exclude.Contains(a.Info.Name)))
			{
				var health = unit.TraitOrDefault<IHealth>();
				if (health == null)
					continue;

				var percent = health.HP * 100 / System.Math.Max(1, health.MaxHP);
				if (retreating.Contains(unit.ActorID))
				{
					if (percent >= Info.ReturnPercent)
					{
						retreating.Remove(unit.ActorID);
						continue;
					}
				}
				else if (percent < Info.RetreatPercent)
					retreating.Add(unit.ActorID);
				else
					continue;

				// Already walking away: leave it be.
				if (unit.CurrentActivity is OpenRA.Mods.Common.Activities.Move)
					continue;

				var refuge = refuges.Where(r => r != unit).MinByOrDefault(r => (r.CenterPosition - unit.CenterPosition).LengthSquared);
				if (refuge != null && (refuge.CenterPosition - unit.CenterPosition).HorizontalLengthSquared > 3 * 3 * 1024 * 1024)
					bot.QueueOrder(new Order("Move", unit, Target.FromCell(world, refuge.Location), false));
			}
		}
	}

	[TraitLocation(SystemActors.Player)]
	[Desc("Keeps one cheap, fast unit exploring the map, so the AI knows where the enemy is.")]
	public class ScoutBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 300;

		[Desc("Unit types used as scouts, in order of preference.")]
		public readonly string[] Scouts = [];

		public override object Create(ActorInitializer init) { return new ScoutBotModule(init.Self, this); }
	}

	public class ScoutBotModule : ConditionalTrait<ScoutBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		uint scoutId;
		int countdown;

		public ScoutBotModule(Actor self, ScoutBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var scout = scoutId != 0 ? world.GetActorById(scoutId) : null;
			if (scout == null || scout.IsDead || !scout.IsInWorld)
			{
				scoutId = 0;
				scout = null;
				foreach (var type in Info.Scouts)
				{
					scout = world.Actors.FirstOrDefault(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.IsIdle && a.Info.Name == type);
					if (scout != null)
						break;
				}

				if (scout == null)
					return;

				scoutId = scout.ActorID;
			}
			else if (!scout.IsIdle)
				return;

			// Somewhere not yet explored, as far from home as luck allows.
			var map = world.Map;
			var best = CPos.Zero;
			var bestDistance = -1;
			for (var i = 0; i < 40; i++)
			{
				var cell = new CPos(world.LocalRandom.Next(map.Bounds.Left, map.Bounds.Right), world.LocalRandom.Next(map.Bounds.Top, map.Bounds.Bottom));
				if (!map.Contains(cell) || player.Shroud.IsExplored(cell))
					continue;

				var distance = (cell - scout.Location).LengthSquared;
				if (distance > bestDistance)
				{
					bestDistance = distance;
					best = cell;
				}
			}

			if (bestDistance >= 0)
				bot.QueueOrder(new Order("Move", scout, Target.FromCell(world, best), false));
		}
	}

	[TraitLocation(SystemActors.Player)]
	[Desc("Sends the AI's drones out to the edge of its weeds, toward the enemy, and the base builder plants weed nodes around them (drones give the build area). " +
		"Weeds let xenos heal and fight better, so the hive creeps across the map.")]
	public class WeedDroneBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 120;

		[Desc("Unit types that act as weed drones.")]
		public readonly string[] Drones = [];

		[Desc("Actor types whose cells count as weeds already.")]
		public readonly string[] Weeds = [];

		[Desc("How far past the nearest weeds a drone goes, in cells (minimum and maximum).")]
		public readonly int MinReach = 5;
		public readonly int MaxReach = 11;

		[Desc("A drone keeps away from spots with enemy units within this many cells.")]
		public readonly int Danger = 8;

		public override object Create(ActorInitializer init) { return new WeedDroneBotModule(init.Self, this); }
	}

	public class WeedDroneBotModule : ConditionalTrait<WeedDroneBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public WeedDroneBotModule(Actor self, WeedDroneBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var drones = world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.IsIdle && Info.Drones.Contains(a.Info.Name)).ToList();
			if (drones.Count == 0)
				return;

			var mine = world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && Info.Weeds.Contains(a.Info.Name)).Select(a => a.Location).ToList();
			if (mine.Count == 0)
				return;

			// Toward the nearest enemy building or unit that is known, else the middle of the map.
			var enemies = world.Actors.Where(a => a.IsInWorld && !a.IsDead && a.OccupiesSpace != null && player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy && a.CanBeViewedByPlayer(player)).ToList();
			var map = world.Map;
			var goal = new CPos(map.Bounds.Left + map.Bounds.Width / 2, map.Bounds.Top + map.Bounds.Height / 2);
			var random = world.LocalRandom;
			var taken = new HashSet<CPos>();

			foreach (var drone in drones)
			{
				var mobile = drone.TraitOrDefault<Mobile>();
				if (mobile == null)
					continue;

				var target = enemies.Count > 0 ? enemies.MinBy(e => (e.Location - drone.Location).LengthSquared).Location : goal;
				CPos best = default;
				var bestScore = int.MaxValue;
				for (var i = 0; i < 30; i++)
				{
					var from = mine[random.Next(mine.Count)];
					var angle = random.Next(1024);
					var reach = random.Next(Info.MinReach, Info.MaxReach + 1);
					var cell = from + new CVec((int)(reach * System.Math.Cos(angle * System.Math.PI / 512)), (int)(reach * System.Math.Sin(angle * System.Math.PI / 512)));
					if (!map.Contains(cell) || taken.Contains(cell) || !mobile.CanEnterCell(cell, drone))
						continue;

					// Past the weeds that are there, not on them.
					if (mine.Any(w => (w - cell).LengthSquared < Info.MinReach * Info.MinReach / 2))
						continue;

					if (enemies.Any(e => !e.Info.HasTraitInfo<BuildingInfo>() && (e.Location - cell).LengthSquared < Info.Danger * Info.Danger))
						continue;

					var score = (cell - target).LengthSquared;
					if (score < bestScore)
					{
						bestScore = score;
						best = cell;
					}
				}

				if (bestScore == int.MaxValue)
					continue;

				taken.Add(best);
				bot.QueueOrder(new Order("Move", drone, Target.FromCell(world, best), false));
			}
		}
	}

	[TraitLocation(SystemActors.Player)]
	[Desc("Uses the caste abilities of the AI's units (ActiveAbility) when they fit: an attack ability when enemies are close, a heal when allies are hurt.")]
	public class AbilityBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 10;

		public override object Create(ActorInitializer init) { return new AbilityBotModule(init.Self, this); }
	}

	public class AbilityBotModule : ConditionalTrait<AbilityBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public AbilityBotModule(Actor self, AbilityBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			foreach (var pair in world.ActorsWithTrait<ActiveAbility>().Where(x => x.Actor.Owner == player && x.Actor.IsInWorld && !x.Actor.IsDead && x.Trait.Ready))
			{
				var unit = pair.Actor;
				var ability = pair.Trait;
				var near = world.FindActorsInCircle(unit.CenterPosition, ability.Info.AiRange).Where(a => !a.IsDead && a.IsInWorld && a != unit).ToList();

				int count;
				if (ability.Info.AiWoundedPercent > 0)
				{
					count = near.Count(a => player.RelationshipWith(a.Owner) == PlayerRelationship.Ally && a.Info.HasTraitInfo<MobileInfo>()
						&& a.TraitOrDefault<IHealth>() is { } h && h.HP * 100 < h.MaxHP * ability.Info.AiWoundedPercent);
					if (unit.TraitOrDefault<IHealth>() is { } own && own.HP * 100 < own.MaxHP * ability.Info.AiWoundedPercent)
						count++;
				}
				else
					count = near.Count(a => player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy && a.Info.HasTraitInfo<MobileInfo>() && a.CanBeViewedByPlayer(player));

				// Shell types and other switches are the player's choice: the AI leaves them as they start.
				if (ability.Info.Toggle || count < ability.Info.AiMinTargets)
					continue;

				if (!ability.IsAimed)
				{
					bot.QueueOrder(new Order(ability.Info.OrderName, unit, false));
					continue;
				}

				var target = AimFor(unit, ability, near);
				if (target.Type != TargetType.Invalid)
					bot.QueueOrder(new Order(ability.Info.OrderName, unit, target, false));
			}
		}

		// Where an aimed ability goes: a heal on the most hurt ally, a unit-aimed attack on the nearest enemy, a spot-aimed one
		// on the enemy with the most other enemies around it.
		Target AimFor(Actor unit, ActiveAbility ability, List<Actor> near)
		{
			if (ability.Info.AiWoundedPercent > 0)
			{
				var hurt = near.Append(unit)
					.Where(a => ability.Info.TargetRelationships.HasRelationship(player.RelationshipWith(a.Owner)) && a.TraitOrDefault<IHealth>() != null)
					.MinByOrDefault(a => a.Trait<IHealth>().HP * 100 / a.Trait<IHealth>().MaxHP);
				return hurt != null ? Target.FromActor(hurt) : Target.Invalid;
			}

			var enemies = near.Where(a => player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy && a.Info.HasTraitInfo<MobileInfo>() && a.CanBeViewedByPlayer(player)).ToList();
			if (enemies.Count == 0)
				return Target.Invalid;

			if (ability.Info.Aim == AbilityAim.TargetActor)
				return Target.FromActor(enemies.MinBy(a => (a.CenterPosition - unit.CenterPosition).LengthSquared));

			// Blasts hurt friends too: skip a spot with one of our own units close to it, the thrower included.
			var two = new WDist(2048).LengthSquared;
			var own = world.FindActorsInCircle(unit.CenterPosition, ability.Info.AiRange + new WDist(2048))
				.Where(a => a.Owner == player && a.Info.HasTraitInfo<MobileInfo>()).ToList();
			var densest = enemies.Where(e => !own.Any(o => (o.CenterPosition - e.CenterPosition).LengthSquared <= two))
				.MaxByOrDefault(a => enemies.Count(b => (b.CenterPosition - a.CenterPosition).LengthSquared <= two));
			return densest != null ? Target.FromCell(world, densest.Location) : Target.Invalid;
		}
	}

	[Desc("Sends idle attackers to the ore fields no one has claimed yet, to disable them. A field that falls is gone; one a marine has repaired is " +
		"a miner, a normal target. Each idle attacker goes for the nearest unclaimed field.")]
	public class FieldBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 120;

		[Desc("The units that go for the fields.")]
		public readonly string[] Attackers = [];

		[Desc("The actor they go for: miner-field for the dormant fields, miner for the marines' miners.")]
		public readonly string Target = "miner-field";

		[Desc("Only targets owned by an enemy player, such as the marines' miners. Off for the dormant fields, which belong to no one.")]
		public readonly bool EnemyOnly = false;

		[Desc("Do not start before this world tick, so the squads get the early game to themselves.")]
		public readonly int MinTick = 0;

		[Desc("The order that sends them. ForceAttack works on a dormant field for engineers (their torch repairs it) and on a miner for xenos.")]
		public readonly string Order = "ForceAttack";

		public override object Create(ActorInitializer init) { return new FieldBotModule(init.Self, this); }
	}

	public class FieldBotModule : ConditionalTrait<FieldBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public FieldBotModule(Actor self, FieldBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0 || world.WorldTick < Info.MinTick)
				return;

			countdown = Info.Interval;
			var taken = new HashSet<Actor>();
			// Dormant fields belong to the Neutral player, which is non-combatant. Miners belong to an enemy player.
			var fields = world.Actors.Where(a => a.Info.Name == Info.Target && a.IsInWorld && !a.IsDead && (Info.EnemyOnly ? player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy : a.Owner.NonCombatant)).ToList();
			if (fields.Count == 0)
				return;

			foreach (var attacker in world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.IsIdle && Info.Attackers.Contains(a.Info.Name)))
			{
				var nearest = fields.OrderBy(f => (f.Location - attacker.Location).LengthSquared);
				// Spread the units out: each goes for the nearest target no other unit got this round. With more units than targets they share.
				var field = nearest.FirstOrDefault(f => !taken.Contains(f)) ?? nearest.First();
				taken.Add(field);
				// An attack order on an actor is refused while the enemy cannot be seen; an attack-move to its cell is not.
				bot.QueueOrder(new Order(Info.Order, attacker, Info.Order == "AttackMove" ? Target.FromCell(world, field.Location) : Target.FromActor(field), false));
			}
		}
	}

	[Desc("Tops up a parallel unit queue (MultiProductionQueue). The stock UnitBuilderBotModule queues a unit only when the queue is empty, so a bot with " +
		"several producers leaves most of them idle and its cash piles up. This queues more units, up to the queue's Slots, from the same unit list, " +
		"limits and delays, once the stock module has started one.")]
	public class ParallelBuildBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 30;

		[Desc("Only queue another unit when the player has at least this much cash and resources.")]
		public readonly int MinCash = 300;

		public override object Create(ActorInitializer init) { return new ParallelBuildBotModule(init.Self, this); }
	}

	public class ParallelBuildBotModule : ConditionalTrait<ParallelBuildBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public ParallelBuildBotModule(Actor self, ParallelBuildBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var builder = player.PlayerActor.Info.TraitInfos<UnitBuilderBotModuleInfo>().FirstOrDefault();
			var resources = player.PlayerActor.TraitOrDefault<PlayerResources>();
			if (builder?.UnitsToBuild == null || resources == null || resources.GetCashAndResources() < Info.MinCash)
				return;

			foreach (var queue in player.PlayerActor.TraitsImplementing<MultiProductionQueue>().Where(q => builder.UnitQueues.Contains(q.Info.Type)))
			{
				// An empty queue is the stock module's to fill; this tops up one that already has something in it.
				var queued = queue.AllQueued().ToList();
				if (queued.Count == 0 || queued.Count >= queue.Slots)
					continue;

				var unit = Choose(queue, builder, queued.Select(i => i.Item).ToList());
				if (unit != null)
					bot.QueueOrder(Order.StartProduction(queue.Actor, unit, 1));
			}
		}

		string Choose(MultiProductionQueue queue, UnitBuilderBotModuleInfo builder, List<string> queuedNames)
		{
			var options = new List<(string Name, int Weight)>();
			foreach (var item in queue.BuildableItems())
			{
				if (!builder.UnitsToBuild.TryGetValue(item.Name, out var weight) || weight <= 0)
					continue;

				if (builder.UnitDelays != null && builder.UnitDelays.TryGetValue(item.Name, out var delay) && world.WorldTick < delay)
					continue;

				if (builder.UnitLimits != null && builder.UnitLimits.TryGetValue(item.Name, out var limit)
					&& world.Actors.Count(a => a.Owner == player && !a.IsDead && a.Info.Name == item.Name) + queuedNames.Count(n => n == item.Name) >= limit)
					continue;

				options.Add((item.Name, weight));
			}

			if (options.Count == 0)
				return null;

			var pick = world.SharedRandom.Next(options.Sum(o => o.Weight));
			foreach (var option in options)
			{
				pick -= option.Weight;
				if (pick < 0)
					return option.Name;
			}

			return options[^1].Name;
		}
	}

	[Desc("Buys upgrades from the Upgrades tab (UpgradeQueue). One at a time, in the palette's order (rifles, then armour, then the rest) and the cheapest first among equals, which follows each ladder " +
		"because a later step needs the one before. The upgrade is paid for as it is built, like a unit, so it only slows the units down a little.")]
	public class UpgradeBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 150;

		[Desc("Do not buy before this world tick, so the first units and buildings come first.")]
		public readonly int MinTick = 2500;

		[Desc("Only start an upgrade when the player has at least this much cash and resources. 0: an upgrade is paid a little at a time, ahead of the unit queues, so it needs no savings.")]
		public readonly int MinCash = 0;

		public override object Create(ActorInitializer init) { return new UpgradeBotModule(init.Self, this); }
	}

	public class UpgradeBotModule : ConditionalTrait<UpgradeBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public UpgradeBotModule(Actor self, UpgradeBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0 || world.WorldTick < Info.MinTick)
				return;

			countdown = Info.Interval;
			var resources = player.PlayerActor.TraitOrDefault<PlayerResources>();
			if (resources == null || resources.GetCashAndResources() < Info.MinCash)
				return;

			foreach (var queue in player.PlayerActor.TraitsImplementing<UpgradeQueue>().Where(q => q.Enabled && !q.AllQueued().Any()))
			{
				// BuildableItems leaves out what is already owned (BuildLimit 1) and what still lacks a building or an earlier step.
				var next = queue.BuildableItems().OrderBy(a => a.TraitInfo<BuildableInfo>().BuildPaletteOrder).ThenBy(a => queue.GetProductionCost(a)).FirstOrDefault();
				if (next != null)
					bot.QueueOrder(Order.StartProduction(queue.Actor, next.Name, 1));
			}
		}
	}

	[Desc("Makes sure the bot has engineers to claim the ore fields: while unclaimed fields exist, it queues engineers until it has Wanted of them " +
		"(alive and queued), never more than there are fields. The stock unit builder picks engineers only now and then, so without this a bot " +
		"can go a whole match without one and never gets a miner's income. FieldBotModule sends them out once they exist.")]
	public class FieldWorkerBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 100;

		[Desc("The engineers to build, the first one this player can build.")]
		public readonly string[] Workers = [];

		[Desc("The actor that marks an unclaimed field.")]
		public readonly string Field = "miner-field";

		[Desc("Engineers to have, as long as there are fields left for them.")]
		public readonly int Wanted = 2;

		public override object Create(ActorInitializer init) { return new FieldWorkerBotModule(init.Self, this); }
	}

	public class FieldWorkerBotModule : ConditionalTrait<FieldWorkerBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public FieldWorkerBotModule(Actor self, FieldWorkerBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var fields = world.Actors.Count(a => a.Info.Name == Info.Field && a.IsInWorld && !a.IsDead && a.Owner.NonCombatant);
			if (fields == 0)
				return;

			var alive = world.Actors.Count(a => a.Owner == player && !a.IsDead && Info.Workers.Contains(a.Info.Name));
			foreach (var queue in player.PlayerActor.TraitsImplementing<ProductionQueue>().Where(q => q.Enabled))
			{
				var worker = Info.Workers.FirstOrDefault(w => queue.BuildableItems().Any(i => i.Name == w));
				if (worker == null)
					continue;

				var queued = queue.AllQueued().Count(i => Info.Workers.Contains(i.Item));
				if (alive + queued < System.Math.Min(Info.Wanted, fields))
					bot.QueueOrder(Order.StartProduction(queue.Actor, worker, 1));

				return;
			}
		}
	}

	[Desc("Guards the marine miners: when a miner has fewer than Wanted defences within Radius cells, the defence is built in the marines' build queue " +
		"and placed on a free cell beside that miner.")]
	public class FieldDefenseBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 150;

		[Desc("Defences wanted around each miner.")]
		public readonly int Wanted = 2;

		[Desc("How far from the miner, in cells, a defence may stand.")]
		public readonly int Radius = 3;

		[Desc("The miner the defences go beside.")]
		public readonly string Miner = "miner";

		[Desc("The defence to build.")]
		public readonly string Defense = "sentry-turret";

		[Desc("The production queue that builds the defence.")]
		public readonly string Queue = "MarineDefense";

		[Desc("Cash and resources needed before a new defence is started.")]
		public readonly int MinCash = 200;

		public override object Create(ActorInitializer init) { return new FieldDefenseBotModule(init.Self, this); }
	}

	public class FieldDefenseBotModule : ConditionalTrait<FieldDefenseBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public FieldDefenseBotModule(Actor self, FieldDefenseBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		int DefencesAround(Actor miner)
		{
			return world.FindActorsInCircle(miner.CenterPosition, WDist.FromCells(Info.Radius))
				.Count(a => a.Owner == player && !a.IsDead && a.Info.Name == Info.Defense);
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var queue = player.PlayerActor.TraitsImplementing<ProductionQueue>().FirstOrDefault(q => q.Info.Type == Info.Queue);
			if (queue == null)
				return;

			var defence = world.Map.Rules.Actors[Info.Defense];
			var building = defence.TraitInfo<BuildingInfo>();
			var miners = world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.Info.Name == Info.Miner).ToList();
			var needy = miners.FirstOrDefault(m => DefencesAround(m) < Info.Wanted);

			// A finished defence waits to be placed beside the miner that needs it.
			var done = queue.AllQueued().FirstOrDefault(i => i.Done && i.Item == Info.Defense);
			if (done != null)
			{
				if (needy == null)
					return;

				for (var r = 2; r <= Info.Radius; r++)
				{
					for (var dx = -r; dx <= r; dx++)
					{
						for (var dy = -r; dy <= r; dy++)
						{
							if (Math.Max(Math.Abs(dx), Math.Abs(dy)) != r)
								continue;

							var cell = needy.Location + new CVec(dx, dy);
							if (!world.CanPlaceBuilding(cell, defence, building, null) || !building.IsCloseEnoughToBase(world, player, defence, cell))
								continue;

							bot.QueueOrder(new Order("PlaceBuilding", player.PlayerActor, Target.FromCell(world, cell), false)
							{
								TargetString = Info.Defense,
								ExtraData = queue.Actor.ActorID,
								SuppressVisualFeedback = true
							});
							return;
						}
					}
				}

				return;
			}

			// Nothing in production yet: start one when a miner needs it and the marines can pay.
			if (needy == null || queue.AllQueued().Any())
				return;

			var resources = player.PlayerActor.TraitOrDefault<PlayerResources>();
			if (resources == null || resources.GetCashAndResources() < Info.MinCash)
				return;

			bot.QueueOrder(Order.StartProduction(queue.Actor, Info.Defense, 1));
		}
	}
}
