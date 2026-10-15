#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Orders;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Spawns an actor on the spot you pick, like SpawnActorPower, and shows a circle of the area it affects while you aim, like the CAS strike does.")]
	public class TgmcSpawnActorPowerInfo : SpawnActorPowerInfo
	{
		[Desc("Radius of the circle shown under the cursor while aiming.")]
		public readonly WDist MarkerRadius = new(3 * 1024);

		public readonly Color MarkerColor = Color.FromArgb(170, 90, 200, 255);

		public override object Create(ActorInitializer init) { return new TgmcSpawnActorPower(init.Self, this); }
	}

	public class TgmcSpawnActorPower : SpawnActorPower
	{
		readonly TgmcSpawnActorPowerInfo info;

		public TgmcSpawnActorPower(Actor self, TgmcSpawnActorPowerInfo info)
			: base(self, info)
		{
			this.info = info;
		}

		public override void SelectTarget(Actor self, string order, SupportPowerManager manager)
		{
			self.World.OrderGenerator = new AreaTargetGenerator(order, manager, info.Cursor, info.BlockedCursor, info.MarkerRadius, info.MarkerColor);
		}
	}

	/// <summary>Aiming a support power at the ground: the order goes out on a click, and a circle follows the mouse.</summary>
	sealed class AreaTargetGenerator : OrderGenerator
	{
		readonly string order;
		readonly SupportPowerManager manager;
		readonly string cursor;
		readonly string blockedCursor;
		readonly WDist radius;
		readonly Color color;

		public AreaTargetGenerator(string order, SupportPowerManager manager, string cursor, string blockedCursor, WDist radius, Color color)
			: base(manager.Self.World)
		{
			this.order = order;
			this.manager = manager;
			this.cursor = cursor;
			this.blockedCursor = blockedCursor;
			this.radius = radius;
			this.color = color;
		}

		protected override MouseActionType ActionType => MouseActionType.SupportPower;

		protected override IEnumerable<Order> OrderInner(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			world.CancelInputMode();
			if (world.Map.Contains(cell))
				yield return new Order(order, manager.Self, Target.FromCell(world, cell), false) { SuppressVisualFeedback = true };
		}

		protected override void Tick(World world)
		{
			if (!manager.Powers.TryGetValue(order, out var p) || !p.Active || !p.Ready)
				world.CancelInputMode();
		}

		protected override IEnumerable<IRenderable> Render(WorldRenderer wr, World world) { yield break; }
		protected override IEnumerable<IRenderable> RenderAboveShroud(WorldRenderer wr, World world) { yield break; }

		protected override IEnumerable<IRenderable> RenderAnnotations(WorldRenderer wr, World world)
		{
			var cell = wr.Viewport.ViewToWorld(Viewport.LastMousePos);
			if (world.Map.Contains(cell))
				yield return new CircleAnnotationRenderable(world.Map.CenterOfCell(cell), radius, 1, color);
		}

		protected override string GetCursor(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			return world.Map.Contains(cell) ? cursor : blockedCursor;
		}
	}
}
