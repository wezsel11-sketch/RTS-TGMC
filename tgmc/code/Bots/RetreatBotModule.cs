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
	[Desc("Pulls badly wounded units back to a refuge (a medbay, a medic or the hive) and lets them return when mended.")]
	public class RetreatBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 20;

		[Desc("A unit below this share of its health retreats.")]
		public readonly int RetreatPercent = 30;

		[Desc("A retreating unit is free to fight again above this share.")]
		public readonly int ReturnPercent = 75;

		[Desc("Actor types that count as a refuge.")]
		public readonly string[] Refuges = [];

		[Desc("Unit types that never retreat.")]
		public readonly string[] Exclude = [];

		public override object Create(ActorInitializer init) { return new RetreatBotModule(init.Self, this); }
	}

	public class RetreatBotModule : ConditionalTrait<RetreatBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		readonly HashSet<uint> retreating = [];
		int countdown;

		public RetreatBotModule(Actor self, RetreatBotModuleInfo info)
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
			var refuges = world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && Info.Refuges.Contains(a.Info.Name)).ToList();
			if (refuges.Count == 0)
				return;

			foreach (var unit in world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.Info.HasTraitInfo<MobileInfo>() && !Info.Exclude.Contains(a.Info.Name)))
			{
				var health = unit.TraitOrDefault<IHealth>();
				if (health == null)
					continue;

				var percent = health.HP * 100 / System.Math.Max(1, health.MaxHP);
				if (retreating.Contains(unit.ActorID))
				{
					if (percent >= Info.ReturnPercent)
					{
						retreating.Remove(unit.ActorID);
						continue;
					}
				}
				else if (percent < Info.RetreatPercent)
					retreating.Add(unit.ActorID);
				else
					continue;

				// Already walking away: leave it be.
				if (unit.CurrentActivity is OpenRA.Mods.Common.Activities.Move)
					continue;

				var refuge = refuges.Where(r => r != unit).MinByOrDefault(r => (r.CenterPosition - unit.CenterPosition).LengthSquared);
				if (refuge != null && (refuge.CenterPosition - unit.CenterPosition).HorizontalLengthSquared > 3 * 3 * 1024 * 1024)
					bot.QueueOrder(new Order("Move", unit, Target.FromCell(world, refuge.Location), false));
			}
		}
	}
}
