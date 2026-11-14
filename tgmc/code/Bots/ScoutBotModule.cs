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
	[Desc("Keeps one cheap, fast unit exploring the map, so the AI knows where the enemy is.")]
	public class ScoutBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 300;

		[Desc("Unit types used as scouts, in order of preference.")]
		public readonly string[] Scouts = [];

		public override object Create(ActorInitializer init) { return new ScoutBotModule(init.Self, this); }
	}

	public class ScoutBotModule : ConditionalTrait<ScoutBotModuleInfo>, IBotTick, IBotNotifyIdleBaseUnits
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

		Actor Scout()
		{
			var scout = scoutId != 0 ? world.GetActorById(scoutId) : null;
			return scout != null && !scout.IsDead && scout.IsInWorld && scout.Owner == player ? scout : null;
		}

		public bool IsScout(Actor a) { return !IsTraitDisabled && scoutId != 0 && a.ActorID == scoutId; }

		// The scout is the scout's: take it out of the squad manager's idle base units, so no squad grabs it between scouting trips.
		void IBotNotifyIdleBaseUnits.UpdatedIdleBaseUnits(List<Actor> idleUnits)
		{
			var scout = IsTraitDisabled ? null : Scout();
			if (scout != null)
				idleUnits.Remove(scout);
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var scout = Scout();
			if (scout == null)
			{
				scoutId = 0;
				foreach (var type in Info.Scouts)
				{
					scout = world.Actors.FirstOrDefault(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.IsIdle && a.Info.Name == type && !BotUnits.Claimed(a));
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
}
