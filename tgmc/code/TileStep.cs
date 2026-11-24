#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
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

	public class TgmcMobile : Mobile, IResolveOrder, ISpeedModifier
	{
		readonly TgmcMobileInfo info;

		// Formation movement: while walking with a group, no faster than its slowest member (a percentage of this unit's own speed).
		// Only while the formation's own move is what the unit is doing: an attack order (which runs no Move of this trait's)
		// must not leave a runner at a crusher's pace.
		readonly Actor owner;
		int formationSpeed = 100;
		OpenRA.Activities.Activity formationMove;

		// Raised by every order this unit gets: FormationMoves drops a pending place once a later order has come in the same tick.
		public int Orders { get; private set; }

		int ISpeedModifier.GetSpeedModifier()
		{
			return formationMove != null && owner.CurrentActivity == formationMove ? formationSpeed : 100;
		}

		// Speed with every modifier on the unit (sticky resin, gas, upgrades), but not the formation's own cap.
		public int CurrentSpeed(Actor self)
		{
			return OpenRA.Mods.Common.Util.ApplyPercentageModifiers(Info.Speed,
				self.TraitsImplementing<ISpeedModifier>().Where(m => m != this).Select(m => m.GetSpeedModifier()));
		}

		public void JoinFormation(int percent, OpenRA.Activities.Activity move)
		{
			formationSpeed = percent;
			formationMove = move;
		}

		public TgmcMobile(ActorInitializer init, TgmcMobileInfo info)
			: base(init, info)
		{
			this.info = info;
			owner = init.Self;
		}

		// Same as Mobile's own handling of orders, except that a Move goes one cell when the tile step option is on.
		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (IsTraitDisabled)
				return;

			// Any new order of its own ends the unit's part in a formation.
			formationMove = null;
			Orders++;

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

					// Units sent to the same cell on the same tick are a group: the world trait sorts them into a formation at the end of the tick.
					if (!order.Queued)
						self.World.WorldActor.TraitOrDefault<FormationMoves>()?.Add(self, this, cell);
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
	[Desc("Formation movement (a lobby option): units ordered to the same cell on the same tick keep their places around the group's " +
		"centre, at most MaxOffset cells out, and walk at the speed of the slowest of them.")]
	public class FormationMovesInfo : TraitInfo
	{
		public readonly int MaxOffset = 3;

		public override object Create(ActorInitializer init) { return new FormationMoves(this); }
	}

	public class FormationMoves
	{
		readonly FormationMovesInfo info;
		readonly List<(Actor Actor, TgmcMobile Mobile, CPos Cell, int Order)> pending = [];

		public FormationMoves(FormationMovesInfo info) { this.info = info; }

		public void Add(Actor self, TgmcMobile mobile, CPos cell)
		{
			if (!Options.Enabled(self.World, Options.Formation, true))
				return;

			if (pending.Count == 0)
				self.World.AddFrameEndTask(Flush);

			pending.Add((self, mobile, cell, mobile.Orders));
		}

		void Flush(World world)
		{
			var orders = pending.ToList();
			pending.Clear();
			foreach (var group in orders.GroupBy(o => (o.Cell, o.Actor.Owner)))
			{
				// A unit given another order later in the tick (a Stop, an attack, a second move) is left to that order.
				var members = group.Where(m => !m.Actor.IsDead && m.Actor.IsInWorld && m.Mobile.Orders == m.Order).ToList();
				if (members.Count < 2)
					continue;

				var cx = members.Sum(m => m.Actor.Location.X) / members.Count;
				var cy = members.Sum(m => m.Actor.Location.Y) / members.Count;
				// shortcut: pace is taken at the order; a member that leaves resin mid-walk keeps the old pace until its next order
				// A stunned member (speed 0) does not hold the whole group still.
				var slowest = members.Select(m => m.Mobile.CurrentSpeed(m.Actor)).Where(v => v > 0).DefaultIfEmpty(0).Min();
				var taken = new HashSet<CPos>();
				foreach (var (actor, mobile, cell, _) in members)
				{
					var dx = System.Math.Clamp(actor.Location.X - cx, -info.MaxOffset, info.MaxOffset);
					var dy = System.Math.Clamp(actor.Location.Y - cy, -info.MaxOffset, info.MaxOffset);
					var want = world.Map.Clamp(new CPos(cell.X + dx, cell.Y + dy));

					// Its own place in the shape, or the nearest cell it could stand on that no other member has.
					var spot = world.Map.FindTilesInCircle(want, 2).OrderBy(c => (c - want).LengthSquared)
						.FirstOrDefault(c => !taken.Contains(c) && mobile.Info.CanEnterCell(world, actor, c, SubCell.FullCell, null, BlockedByActor.Immovable));
					if (spot == default)
						continue;

					taken.Add(spot);
					var move = new Move(actor, spot, WDist.Zero, null, true, mobile.Info.TargetLineColor);
					actor.CancelActivity();
					actor.QueueActivity(move);
					var speed = mobile.CurrentSpeed(actor);
					if (speed > 0 && slowest > 0)
						mobile.JoinFormation(slowest * 100 / speed, move);
				}
			}
		}
	}
}
