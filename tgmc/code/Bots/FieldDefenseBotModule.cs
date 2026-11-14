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
