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
}
