#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Graphics;
using OpenRA.Mods.Common.Orders;
using OpenRA.Mods.TGMC.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Orders
{
	// After pressing an aimed ability's button: the next left click picks where it goes (a spot, or a unit for Aim: TargetActor),
	// right click cancels. Each caster that has the ability ready gets the order; one out of reach walks into reach first.
	public class AbilityOrderGenerator : UnitOrderGenerator
	{
		readonly Actor[] casters;
		readonly ActiveAbilityInfo info;

		public string OrderName => info.OrderName;

		protected override MouseActionType ActionType => MouseActionType.ConfirmOrder;

		public AbilityOrderGenerator(World world, IEnumerable<Actor> casters, ActiveAbilityInfo info)
			: base(world)
		{
			this.casters = casters.ToArray();
			this.info = info;
		}

		protected override IEnumerable<Order> OrderInner(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			var target = PickTarget(world, cell, mi);
			if (target.Type == TargetType.Invalid)
				yield break;

			var queued = mi.Modifiers.HasModifier(Modifiers.Shift);
			if (!queued)
				world.CancelInputMode();
			else
				HasIssuedQueuedCommand = true;

			foreach (var a in casters.Where(Ready))
				yield return new Order(info.OrderName, a, target, queued);
		}

		Target PickTarget(World world, CPos cell, MouseInput mi)
		{
			if (info.Aim != AbilityAim.TargetActor)
				return world.Map.Contains(cell) ? Target.FromCell(world, cell) : Target.Invalid;

			var owner = casters.FirstOrDefault()?.Owner;
			var actor = world.ScreenMap.ActorsAtMouse(mi).Select(a => a.Actor)
				.FirstOrDefault(a => owner != null && !a.IsDead && info.TargetRelationships.HasRelationship(owner.RelationshipWith(a.Owner)));
			return actor != null ? Target.FromActor(actor) : Target.Invalid;
		}

		bool Ready(Actor a)
		{
			return a.IsInWorld && !a.IsDead && a.TraitsImplementing<ActiveAbility>().Any(x => x.Info.OrderName == info.OrderName && x.Ready);
		}

		public override string GetCursor(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			var target = PickTarget(world, cell, mi);
			if (target.Type == TargetType.Invalid)
				return "move-blocked";

			var first = casters.FirstOrDefault(Ready);
			return first != null && (target.CenterPosition - first.CenterPosition).HorizontalLengthSquared > info.Range.LengthSquared ? "move" : "ability";
		}

		// The reach of the first caster, so the player sees where it fires without walking.
		public override IEnumerable<IRenderable> RenderAnnotations(WorldRenderer wr, World world)
		{
			var first = casters.FirstOrDefault(Ready);
			if (first != null)
				yield return new RangeCircleAnnotationRenderable(first.CenterPosition, info.Range, 0, Color.FromArgb(160, 255, 208, 64), 1, Color.FromArgb(96, 0, 0, 0), 3);
		}

		public override void Tick(World world)
		{
			if (!casters.Any(Ready))
				world.CancelInputMode();
		}
	}
}
