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
using OpenRA.Mods.Common.Traits.BotModules.Squads;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("Sends a small group of fast units at the enemy's most valuable, least defended outpost (a lone miner, an outlying field) " +
		"by a way round the defences ThreatMemory knows of, and turns it home when it meets more than it can beat. One raid at a time.")]
	public class RaidBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 50;

		[Desc("Fast unit types that raid.")]
		public readonly string[] Raiders = [];

		[Desc("Units in a raid. No raid sets off with fewer.")]
		public readonly int Size = 4;

		[Desc("Enemy actor types worth raiding.")]
		public readonly string[] Targets = [];

		[Desc("Only targets whose remembered defence is at most this percent of the raid's value.")]
		public readonly int MaxThreatPercent = 60;

		[Desc("The raid turns home when the strength around it passes this percent of its remaining value.")]
		public readonly int BackOffPercent = 120;

		[Desc("Cells around a target, or around the raid, counted for defence.")]
		public readonly int Radius = 4;

		[Desc("The bot's own actors that mark its base: the raid comes home to the nearest.")]
		public readonly string[] BaseTypes = ["resin-silo"];

		public override object Create(ActorInitializer init) { return new RaidBotModule(init.Self, this); }
	}

	public class RaidBotModule : ConditionalTrait<RaidBotModuleInfo>, IBotTick, IBotNotifyIdleBaseUnits
	{
		const int HomewardTimeout = 500;
		readonly World world;
		readonly Player player;
		readonly List<Actor> raid = [];
		readonly List<Actor> released = [];
		ThreatMemory memory;
		MinerGuardBotModule[] guards = [];
		DefendBotModule[] defenders = [];
		List<CPos> route = [];
		List<(CPos Cell, int Value)> candidates = [];
		CPos target;
		int targetValue;
		int leg;
		bool homeward;
		int homewardSince;
		bool ordered;
		int countdown;

		public RaidBotModule(Actor self, RaidBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		protected override void Created(Actor self)
		{
			base.Created(self);
			memory = self.TraitOrDefault<ThreatMemory>();
			guards = self.TraitsImplementing<MinerGuardBotModule>().ToArray();
			defenders = self.TraitsImplementing<DefendBotModule>().ToArray();
		}

		public bool IsRaider(Actor a) { return !IsTraitDisabled && raid.Contains(a); }

		bool Free(Actor a)
		{
			return !a.IsDead && a.IsInWorld && a.Owner == player && Info.Raiders.Contains(a.Info.Name)
				&& !guards.Any(g => g.IsGuard(a)) && !defenders.Any(d => d.IsBusy(a));
		}

		// Enemy actors of the Targets types this player knows of: in sight now, or remembered as frozen (or all, with FullVision).
		IEnumerable<(CPos Cell, int Value)> Candidates()
		{
			var seen = world.Actors.Where(a => a.IsInWorld && !a.IsDead && Info.Targets.Contains(a.Info.Name)
					&& player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy && (memory.FullVision || a.CanBeViewedByPlayer(player)))
				.Select(a => (a.Location, BotUnits.Value(a)));
			var frozen = player.FrozenActorLayer?.FrozenActorsInRegion(world.Map.AllCells)
				.Where(f => f.IsValid && f.Visible && Info.Targets.Contains(f.Info.Name) && player.RelationshipWith(f.Owner) == PlayerRelationship.Enemy)
				.Select(f => (world.Map.CellContaining(f.CenterPosition), f.Info.TraitInfoOrDefault<ValuedInfo>()?.Cost ?? 0)) ?? [];
			return seen.Concat(frozen);
		}

		void IBotNotifyIdleBaseUnits.UpdatedIdleBaseUnits(List<Actor> idleUnits)
		{
			if (IsTraitDisabled || memory == null)
				return;

			idleUnits.AddRange(released.Where(a => !a.IsDead && a.IsInWorld));
			released.Clear();
			if (raid.Count > 0)
				return;

			var free = idleUnits.Where(Free).Take(Info.Size).ToList();
			if (free.Count < Info.Size)
				return;

			var value = free.Sum(BotUnits.Value);
			var options = candidates.Where(c => memory.DefenceNear(c.Cell, c.Value, Info.Radius) * 100 <= value * Info.MaxThreatPercent).ToList();
			if (options.Count == 0)
				return;

			var best = memory.WeakestTarget(options, c => c.Cell, c => c.Value, Info.Radius);
			target = best.Cell;
			targetValue = best.Value;
			var centre = free[0].Location;
			route = memory.SafePath(centre, target);
			leg = 0;
			homeward = false;
			ordered = false;
			foreach (var a in free)
				idleUnits.Remove(a);

			raid.AddRange(free);
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || memory == null || --countdown > 0)
				return;

			countdown = Info.Interval;
			raid.RemoveAll(a => a.IsDead || !a.IsInWorld || a.Owner != player);
			if (raid.Count == 0)
			{
				// The squad manager hands over its idle units every tick: the scan for targets runs here, once per Interval.
				candidates = Candidates().ToList();
				return;
			}

			var centre = new CPos((int)raid.Average(a => a.Location.X), (int)raid.Average(a => a.Location.Y));
			if (homeward)
			{
				// A raider stuck on the way (blocked, or chasing something) must not hold the next raid back for ever.
				if (raid.All(a => a.IsIdle) || world.WorldTick - homewardSince > HomewardTimeout)
				{
					released.AddRange(raid);
					raid.Clear();
				}

				return;
			}

			var value = raid.Sum(BotUnits.Value);
			var atEnd = leg >= route.Count - 1;
			// The target's own value is not defence: wherever the count takes the target in, count only what stands around it.
			// (The count goes by whole grid squares, so it takes the target in from up to a square further out than Radius: a raid
			// worth less than its target used to turn home there, some four to eight cells short, and never arrive.)
			var around = memory.Counts(centre, Info.Radius, target) ? memory.DefenceNear(centre, targetValue, Info.Radius) : memory.StrengthNear(centre, Info.Radius);
			if (around * 100 > value * Info.BackOffPercent || (atEnd && ordered && raid.All(a => a.IsIdle)))
			{
				// Outmatched, or done: nothing left to hit at the target.
				homeward = true;
				homewardSince = world.WorldTick;
				foreach (var a in raid)
					BotUnits.SendHome(bot, a, Info.BaseTypes);

				return;
			}

			if (ordered && !atEnd && ((centre - route[leg]).LengthSquared <= 9 || raid.All(a => a.IsIdle)))
			{
				leg++;
				ordered = false;
			}

			if (!ordered)
			{
				// Walk the way round (a plain move, so the raid does not stop to fight what it passes); attack only on the last leg.
				var order = leg >= route.Count - 1 ? "AttackMove" : "Move";
				foreach (var a in raid)
					bot.QueueOrder(new Order(order, a, Target.FromCell(world, route[leg]), false));

				ordered = true;
			}
		}
	}
}
