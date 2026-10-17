#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Activities;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Graphics;
using OpenRA.Mods.Common.Orders;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Patrol: the unit walks between where it stands and the cell you pick, forever, until you give it another order (classic RTS patrol).")]
	public class PatrolInfo : TraitInfo, Requires<IMoveInfo>
	{
		public readonly string Cursor = "move";
		public readonly string BlockedCursor = "move-blocked";

		public override object Create(ActorInitializer init) { return new Patrol(init.Self, this); }
	}

	public class Patrol : IResolveOrder
	{
		readonly PatrolInfo info;
		readonly IMove move;

		public Patrol(Actor self, PatrolInfo info)
		{
			this.info = info;
			move = self.Trait<IMove>();
		}

		public void ResolveOrder(Actor self, Order order)
		{
			if (order.OrderString != "Patrol" || !order.Target.IsValidFor(self))
				return;

			var far = self.World.Map.Clamp(self.World.Map.CellContaining(order.Target.CenterPosition));
			var here = self.Location;
			self.QueueActivity(order.Queued, new PatrolActivity(move, here, far));
		}
	}

	/// <summary>Walks to one end of the patrol and then the other, again and again. Any later order (queued or not) takes over.</summary>
	sealed class PatrolActivity : Activity
	{
		readonly IMove move;
		readonly CPos first;
		readonly CPos second;
		bool towardsSecond = true;

		public PatrolActivity(IMove move, CPos first, CPos second)
		{
			this.move = move;
			this.first = first;
			this.second = second;
		}

		public override bool Tick(Actor self)
		{
			if (IsCanceling)
				return true;

			var next = towardsSecond ? second : first;
			towardsSecond = !towardsSecond;
			QueueChild(move.MoveTo(next, 2, evaluateNearestMovableCell: true));
			return false;
		}
	}

	/// <summary>Picking the far end of a patrol with the Patrol button: a click issues the order to every selected unit that can patrol.</summary>
	public class PatrolOrderGenerator : UnitOrderGenerator
	{
		readonly IEnumerable<Actor> subjects;

		protected override MouseActionType ActionType => MouseActionType.ConfirmOrder;

		public PatrolOrderGenerator(World world, IEnumerable<Actor> selected)
			: base(world)
		{
			subjects = selected.Where(a => !a.IsDead && a.Info.HasTraitInfo<PatrolInfo>()).ToArray();
		}

		protected override IEnumerable<Order> OrderInner(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			var queued = mi.Modifiers.HasModifier(Modifiers.Shift);
			if (!queued)
				world.CancelInputMode();
			else
				HasIssuedQueuedCommand = true;

			cell = world.Map.Clamp(cell);
			yield return new Order("Patrol", null, Target.FromCell(world, cell), queued, null, subjects.ToArray());
		}

		public override IEnumerable<IRenderable> RenderAnnotations(WorldRenderer wr, World world)
		{
			var cell = wr.Viewport.ViewToWorld(Viewport.LastMousePos);
			if (world.Map.Contains(cell))
				yield return new CircleAnnotationRenderable(world.Map.CenterOfCell(cell), new WDist(1024), 1, Color.FromArgb(170, 90, 200, 255));
		}
	}
}
