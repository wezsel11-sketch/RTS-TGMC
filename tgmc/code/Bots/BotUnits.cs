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

// Extra modules for the skirmish AI. The engine's own modules build the base, train a fixed mix and send squads out; these add what a
// player would do on top: pick units to counter what the enemy fields, evolve, bring medics to the wounded, pull wounded units back
// and scout the map. Each one is switched on by a condition in ai.yaml, so the difficulty levels can leave some of them out.
namespace OpenRA.Mods.TGMC.Traits
{
	static class BotUnits
	{
		public static int Value(Actor a) { return a.Info.TraitInfoOrDefault<ValuedInfo>()?.Cost ?? 0; }

		// True when one of the owner's bot modules holds this unit (a miner guard, a defender or a raider): other modules leave it be.
		public static bool Claimed(Actor a)
		{
			var p = a.Owner.PlayerActor;
			return p.TraitsImplementing<MinerGuardBotModule>().Any(m => m.IsGuard(a))
				|| p.TraitsImplementing<DefendBotModule>().Any(m => m.IsBusy(a))
				|| p.TraitsImplementing<RaidBotModule>().Any(m => m.IsRaider(a))
				|| p.TraitsImplementing<ScoutBotModule>().Any(m => m.IsScout(a))
				|| p.TraitsImplementing<ObjectiveBotModule>().Any(m => m.IsHolder(a));
		}

		// A unit handed back to the squad manager walks to the nearest of its owner's base actors, so it idles where the squads gather.
		public static void SendHome(IBot bot, Actor unit, string[] baseTypes)
		{
			if (unit.IsDead || !unit.IsInWorld)
				return;

			var home = unit.World.Actors.Where(a => a.Owner == unit.Owner && a.IsInWorld && !a.IsDead && baseTypes.Contains(a.Info.Name))
				.MinByOrDefault(a => (a.Location - unit.Location).LengthSquared);
			if (home != null)
				bot.QueueOrder(new Order("Move", unit, Target.FromCell(unit.World, home.Location), false));
		}
	}
}
