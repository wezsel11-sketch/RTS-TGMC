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
	[Desc("Buys upgrades from the Upgrades tab (UpgradeQueue). One at a time, in the palette's order (rifles, then armour, then the rest) and the cheapest first among equals, which follows each ladder " +
		"because a later step needs the one before. The upgrade is paid for as it is built, ahead of the units, so it waits for an army first (MinArmy).")]
	public class UpgradeBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 150;

		[Desc("Do not buy before this world tick, so the first units and buildings come first.")]
		public readonly int MinTick = 2500;

		[Desc("Only start an upgrade when the player has at least this much cash and resources. 0: an upgrade is paid a little at a time, ahead of the unit queues, so it needs no savings.")]
		public readonly int MinCash = 0;

		[Desc("Only start an upgrade while the bot has at least this many mobile fighting units. The Upgrade queue is paid ahead of the unit " +
			"queues, so an upgrade takes every coin until it is done: started with no army, the marine ladders (about 9000 in all) kept it from ever growing one.")]
		public readonly int MinArmy = 0;

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

			if (Info.MinArmy > 0 && world.ActorsHavingTrait<AttackBase>().Count(a => a.Owner == player && !a.IsDead && a.Info.HasTraitInfo<MobileInfo>()) < Info.MinArmy)
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
}
