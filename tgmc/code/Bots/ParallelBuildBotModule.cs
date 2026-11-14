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
}
