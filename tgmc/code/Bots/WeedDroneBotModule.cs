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
}
