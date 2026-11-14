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
	[Desc("Aims the squad manager's attack squads at the enemy structure with the most value for the least defence ThreatMemory knows " +
		"of, among those the squad outmatches; with none it outmatches, the squad keeps the stock squad manager's own target. A squad " +
		"fighting enemy units keeps that fight.")]
	public class AttackTargetBotModuleInfo : ConditionalTraitInfo
	{
		[Desc("Ticks between looks. Short: the stock squad picks the nearest structure when it forms and whenever one comes in its scan radius.")]
		public readonly int Interval = 25;

		[Desc("Enemy actor types worth attacking.")]
		public readonly string[] Targets = [];

		[Desc("A target qualifies when the squad's value is at least this percent of the defence around it.")]
		public readonly int OutmatchPercent = 130;

		[Desc("Cells around a target counted for its defence.")]
		public readonly int Radius = 6;

		[Desc("A squad with enemy units in sight this close is left to its fight.")]
		public readonly int FightRadius = 8;

		public override object Create(ActorInitializer init) { return new AttackTargetBotModule(init.Self, this); }
	}

	public class AttackTargetBotModule : ConditionalTrait<AttackTargetBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		ThreatMemory memory;
		SquadManagerBotModule[] managers = [];
		int countdown;

		public AttackTargetBotModule(Actor self, AttackTargetBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		protected override void Created(Actor self)
		{
			base.Created(self);
			memory = self.TraitOrDefault<ThreatMemory>();
			managers = self.TraitsImplementing<SquadManagerBotModule>().ToArray();
		}

		// Enemy Targets this player knows of: in sight, or remembered as frozen (or all, with FullVision). A target needs a live actor to aim at.
		List<Actor> Candidates()
		{
			var known = world.Actors.Where(a => a.IsInWorld && !a.IsDead && Info.Targets.Contains(a.Info.Name)
				&& player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy && (memory.FullVision || a.CanBeViewedByPlayer(player)));
			var frozen = player.FrozenActorLayer?.FrozenActorsInRegion(world.Map.AllCells)
				.Where(f => f.IsValid && f.Visible && f.Actor != null && !f.Actor.IsDead && Info.Targets.Contains(f.Info.Name)
					&& player.RelationshipWith(f.Owner) == PlayerRelationship.Enemy)
				.Select(f => f.Actor) ?? [];
			return known.Concat(frozen).Distinct().ToList();
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || memory == null || --countdown > 0)
				return;

			countdown = Info.Interval;
			List<Actor> candidates = null;
			foreach (var squad in managers.Where(m => !m.IsTraitDisabled).SelectMany(m => m.Squads))
			{
				if (!squad.IsValid || (squad.Type != SquadType.Assault && squad.Type != SquadType.Rush))
					continue;

				candidates ??= Candidates();
				var value = squad.Units.Where(u => !u.IsDead).Sum(BotUnits.Value);
				var best = memory.WeakestTarget(
					candidates.Where(t => memory.DefenceNear(t.Location, BotUnits.Value(t), Info.Radius) * Info.OutmatchPercent <= value * 100),
					t => t.Location, BotUnits.Value, Info.Radius);
				// Leave a squad fighting enemy units alone (its target is not readable from here, so judge by what stands near it).
				var fighting = world.FindActorsInCircle(squad.CenterPosition(), WDist.FromCells(Info.FightRadius))
					.Any(e => !e.IsDead && player.RelationshipWith(e.Owner) == PlayerRelationship.Enemy && e.Info.HasTraitInfo<MobileInfo>()
						&& e.CanBeViewedByPlayer(player));
				if (best != null && !fighting)
				{
					squad.SetActorToTarget((best, WVec.Zero));

					// The stock idle state sets off only once it sees an enemy near its target, and a target picked from memory is
					// usually under fog: the squad then stood at home all game. Walk it there; in sight, the stock states take over.
					var units = squad.Units.Where(u => !u.IsDead && u.IsInWorld).ToArray();
					if (units.Length > 0 && units.All(u => u.IsIdle))
						bot.QueueOrder(new Order("AttackMove", null, Target.FromActor(best), false, groupedActors: units));
				}
			}
		}
	}
}
