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
	[Desc("Sends medics to the wounded and infected, and otherwise keeps them close to the fighting units.")]
	public class MedicBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 40;

		[Desc("Unit types that act as medics.")]
		public readonly string[] Medics = [];

		[Desc("Units below this share of their health count as wounded.")]
		public readonly int WoundedPercent = 75;

		public override object Create(ActorInitializer init) { return new MedicBotModule(init.Self, this); }
	}

	public class MedicBotModule : ConditionalTrait<MedicBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public MedicBotModule(Actor self, MedicBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		bool Needs(Actor a)
		{
			if (a.TraitOrDefault<Infestable>() is { IsInfected: true })
				return true;

			var health = a.TraitOrDefault<IHealth>();
			return health != null && health.HP * 100 < health.MaxHP * Info.WoundedPercent;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var own = world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.Info.HasTraitInfo<MobileInfo>()).ToList();
			var medics = own.Where(a => Info.Medics.Contains(a.Info.Name) && a.IsIdle).ToList();
			if (medics.Count == 0)
				return;

			var patients = own.Where(a => !Info.Medics.Contains(a.Info.Name) && a.Info.HasTraitInfo<InfestableInfo>() && Needs(a)).ToList();
			var soldiers = own.Where(a => !Info.Medics.Contains(a.Info.Name) && !a.IsIdle && a.Info.HasTraitInfo<AttackBaseInfo>()).ToList();

			foreach (var medic in medics)
			{
				Actor goal = null;
				if (patients.Count > 0)
				{
					goal = patients.MinBy(p => (p.CenterPosition - medic.CenterPosition).LengthSquared);
					patients.Remove(goal);
				}
				else if (soldiers.Count > 0)
				{
					// No one to heal: stay with the fighting units, so help is near when they are hit.
					goal = soldiers.MinBy(s => (s.CenterPosition - medic.CenterPosition).LengthSquared);
					if ((goal.CenterPosition - medic.CenterPosition).HorizontalLengthSquared < 6 * 6 * 1024 * 1024)
						continue;
				}

				if (goal != null)
					bot.QueueOrder(new Order("Move", medic, Target.FromCell(world, goal.Location), false));
			}
		}
	}
}
