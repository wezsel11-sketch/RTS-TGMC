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
}
