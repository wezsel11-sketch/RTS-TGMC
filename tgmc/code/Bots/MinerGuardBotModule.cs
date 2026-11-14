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
	[Desc("Keeps a few fighters standing beside each of the bot's miners. The stock squad manager only sends units that idle at the main base, " +
		"and a miner far from it was disabled before any arrived. Guards are taken from the squad manager's idle units, so no squad pulls them " +
		"away, and handed back when their miner is gone.")]
	public class MinerGuardBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 50;

		[Desc("Guards kept beside each miner.")]
		public readonly int GuardsPerMiner = 2;

		[Desc("The actor they guard.")]
		public readonly string Miner = "miner";

		[Desc("Unit types that may guard.")]
		public readonly string[] Guards = [];

		[Desc("An idle guard further than this many cells from its miner walks back.")]
		public readonly int Leash = 3;

		[Desc("Miners within this many cells of one of the bot's BaseTypes get no guards: the units idling at the base already cover them.")]
		public readonly int BaseRadius = 12;

		[Desc("The bot's own actors that mark its base.")]
		public readonly string[] BaseTypes = ["cryo-pod"];

		public override object Create(ActorInitializer init) { return new MinerGuardBotModule(init.Self, this); }
	}

	public class MinerGuardBotModule : ConditionalTrait<MinerGuardBotModuleInfo>, IBotTick, IBotNotifyIdleBaseUnits
	{
		readonly World world;
		readonly Player player;
		readonly Dictionary<Actor, Actor> minerOf = [];
		readonly List<Actor> released = [];
		List<Actor> farMiners = [];
		int countdown;

		public MinerGuardBotModule(Actor self, MinerGuardBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		public bool IsGuard(Actor a) { return !IsTraitDisabled && minerOf.ContainsKey(a); }

		// The squad manager passes its own list of idle base units: a unit removed from it is ours until handed back by adding it again.
		void IBotNotifyIdleBaseUnits.UpdatedIdleBaseUnits(List<Actor> idleUnits)
		{
			if (IsTraitDisabled)
				return;

			idleUnits.AddRange(released.Where(a => !a.IsDead));
			released.Clear();

			// The squad manager calls this every tick: the map scan for far miners runs in BotTick, once per Interval.
			foreach (var miner in farMiners.Where(m => !m.IsDead && m.IsInWorld && m.Owner == player))
			{
				for (var have = minerOf.Values.Count(m => m == miner); have < Info.GuardsPerMiner; have++)
				{
					var guard = idleUnits.Where(a => !a.IsDead && a.IsInWorld && Info.Guards.Contains(a.Info.Name))
						.MinByOrDefault(a => (a.CenterPosition - miner.CenterPosition).LengthSquared);
					if (guard == null)
						return;

					idleUnits.Remove(guard);
					minerOf[guard] = miner;
				}
			}
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var bases = world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && Info.BaseTypes.Contains(a.Info.Name)).ToList();
			// The furthest from home first: with few fighters, the most exposed miner gets its guards before the safer ones.
			farMiners = world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.Info.Name == Info.Miner
				&& !bases.Any(b => (a.Location - b.Location).LengthSquared <= Info.BaseRadius * Info.BaseRadius))
				.OrderByDescending(a => bases.Count == 0 ? 0 : bases.Min(b => (a.Location - b.Location).LengthSquared)).ToList();
			foreach (var (guard, miner) in minerOf.ToList())
			{
				if (guard.IsDead || guard.Owner != player)
					minerOf.Remove(guard);
				else if (miner.IsDead || miner.Owner != player)
				{
					minerOf.Remove(guard);
					released.Add(guard);
					BotUnits.SendHome(bot, guard, Info.BaseTypes);
				}
				else if (guard.IsInWorld && guard.IsIdle && (guard.Location - miner.Location).LengthSquared > Info.Leash * Info.Leash)
					bot.QueueOrder(new Order("AttackMove", guard, Target.FromCell(world, miner.Location), false));
			}
		}
	}
}
