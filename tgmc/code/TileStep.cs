#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Mods.Common.Activities;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("The normal Mobile, plus a lobby option for tile by tile movement: with it on, a move order walks only one cell " +
		"toward where you clicked, like clicking to step in SS13. Click again for the next step.")]
	public class TgmcMobileInfo : MobileInfo
	{
		public override object Create(ActorInitializer init) { return new TgmcMobile(init, this); }
	}

	public class TgmcMobile : Mobile, IResolveOrder
	{
		readonly TgmcMobileInfo info;

		public TgmcMobile(ActorInitializer init, TgmcMobileInfo info)
			: base(init, info)
		{
			this.info = info;
		}

		// Same as Mobile's own handling of orders, except that a Move goes one cell when the tile step option is on.
		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (IsTraitDisabled)
				return;

			if (order.OrderString == "Move")
			{
				if (!order.Target.IsValidFor(self))
					return;

				var cell = self.World.Map.Clamp(self.World.Map.CellContaining(order.Target.CenterPosition));
				if (!info.LocomotorInfo.MoveIntoShroud && !self.Owner.Shroud.IsExplored(cell))
					return;

				if (Options.Enabled(self.World, Options.TileStep, false))
				{
					var here = self.Location;
					var step = new CPos(here.X + System.Math.Sign(cell.X - here.X), here.Y + System.Math.Sign(cell.Y - here.Y));
					if (step == here)
						return;

					cell = step;
					self.QueueActivity(order.Queued, new Move(self, cell, WDist.Zero, null, true, info.TargetLineColor));
				}
				else
				{
					self.QueueActivity(order.Queued, new Move(self, cell, WDist.FromCells(8), null, true, info.TargetLineColor));
				}

				self.ShowTargetLines();
			}
			else if (order.OrderString == "Stop")
				self.CancelActivity();
			else if (order.OrderString == "Scatter")
			{
				self.QueueActivity(order.Queued, new Nudge(self));
				self.ShowTargetLines();
			}
		}
	}
}
