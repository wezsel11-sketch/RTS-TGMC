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

				if (count >= ability.Info.AiMinTargets)
					bot.QueueOrder(new Order(ability.Info.OrderName, unit, false));
			}
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
			if (IsTraitDisabled || --countdown > 0)
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
				bot.QueueOrder(new Order(Info.Order, attacker, Target.FromActor(field), false));
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
