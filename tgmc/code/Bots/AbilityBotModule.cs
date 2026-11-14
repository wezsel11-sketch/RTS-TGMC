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
	[Desc("Uses the caste abilities of the AI's units (ActiveAbility) when they fit: an attack ability when enemies are close, a heal when allies are hurt.")]
	public class AbilityBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 10;

		public override object Create(ActorInitializer init) { return new AbilityBotModule(init.Self, this); }
	}

	public class AbilityBotModule : ConditionalTrait<AbilityBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public AbilityBotModule(Actor self, AbilityBotModuleInfo info)
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
			foreach (var pair in world.ActorsWithTrait<ActiveAbility>().Where(x => x.Actor.Owner == player && x.Actor.IsInWorld && !x.Actor.IsDead && x.Trait.Ready))
			{
				// Shell types and other switches are the player's choice: AutoTarget leaves them as they start.
				var target = pair.Trait.AutoTarget(pair.Actor);
				if (target is { } t)
					bot.QueueOrder(t.Type == TargetType.Invalid
						? new Order(pair.Trait.Info.OrderName, pair.Actor, false)
						: new Order(pair.Trait.Info.OrderName, pair.Actor, t, false));
			}
		}
	}
}
