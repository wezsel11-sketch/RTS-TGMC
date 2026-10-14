#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Orders;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Scripting;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("The Queen's screech: the Deploy key stuns every enemy infantry unit within range for a few seconds, then needs time to recover.")]
	public class ScreechInfo : ConditionalTraitInfo
	{
		[Desc("Ticks before the screech can be used again.")]
		public readonly int Cooldown = 900;

		public readonly WDist Range = WDist.FromCells(7);

		[Desc("Ticks the victims stay stunned.")]
		public readonly int StunDuration = 75;

		[Desc("The condition victims receive. Units grant it through an ExternalCondition of this name.")]
		public readonly string Condition = "stunned";

		[Desc("Target types the screech works on.")]
		public readonly BitSet<TargetableType> ValidTargets = default;

		public readonly string[] Sounds = [];
		public readonly string EffectImage = null;
		public readonly string EffectSequence = null;
		public readonly string Palette = "effect";

		[Desc("Cursor shown over the unit when the Deploy key would screech.")]
		public readonly string Cursor = "deploy";

		public override object Create(ActorInitializer init) { return new Screech(this); }
	}

	public class Screech : ConditionalTrait<ScreechInfo>, IIssueOrder, IResolveOrder, IIssueDeployOrder, ITick, ISelectionBar
	{
		int cooldown;

		public Screech(ScreechInfo info)
			: base(info) { }

		public int CooldownRemaining => cooldown;

		float ISelectionBar.GetValue() { return cooldown > 0 ? 1f - cooldown / (float)System.Math.Max(1, Info.Cooldown) : 0f; }
		Color ISelectionBar.GetColor() { return Color.FromArgb(200, 120, 255); }
		bool ISelectionBar.DisplayWhenEmpty => false;

		void ITick.Tick(Actor self)
		{
			if (cooldown > 0)
				cooldown--;
		}

		IEnumerable<IOrderTargeter> IIssueOrder.Orders
		{
			get { yield return new DeployOrderTargeter("Screech", 6, () => Info.Cursor); }
		}

		Order IIssueOrder.IssueOrder(Actor self, IOrderTargeter order, in Target target, bool queued)
		{
			return order.OrderID == "Screech" ? new Order(order.OrderID, self, queued) : null;
		}

		Order IIssueDeployOrder.IssueDeployOrder(Actor self, bool queued) { return new Order("Screech", self, queued); }
		bool IIssueDeployOrder.CanIssueDeployOrder(Actor self, bool queued) { return !IsTraitDisabled && cooldown == 0; }

		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (order.OrderString != "Screech" || IsTraitDisabled || cooldown > 0)
				return;

			cooldown = Info.Cooldown;
			var world = self.World;

			foreach (var victim in world.FindActorsInCircle(self.CenterPosition, Info.Range))
			{
				if (victim.IsDead || !victim.IsInWorld || self.Owner.RelationshipWith(victim.Owner) != PlayerRelationship.Enemy)
					continue;

				if (!Info.ValidTargets.IsEmpty && !victim.GetEnabledTargetTypes().Overlaps(Info.ValidTargets))
					continue;

				var grant = victim.TraitsImplementing<ExternalCondition>().FirstOrDefault(c => c.Info.Condition == Info.Condition && c.CanGrantCondition(self));
				grant?.GrantCondition(victim, self, Info.StunDuration);
			}

			Fx.Sound(world, self.CenterPosition, Info.Sounds);
			Fx.Sprite(world, self.CenterPosition, Info.EffectImage, Info.EffectSequence, Info.Palette);
			TgmcEventLog.Post(world, self.Owner, "event-screech", self.CenterPosition);
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using OpenRA.Mods.TGMC.Traits;

	[ScriptPropertyGroup("Combat")]
	public class ScreechProperties : ScriptActorProperties, Requires<ScreechInfo>
	{
		readonly Screech screech;

		public ScreechProperties(ScriptContext context, Actor self)
			: base(context, self)
		{
			screech = self.Trait<Screech>();
		}

		[Desc("Screech now, as if the Deploy key were pressed. Does nothing while the screech recovers.")]
		public void Screech()
		{
			((IResolveOrder)screech).ResolveOrder(Self, new Order("Screech", Self, false));
		}
	}
}
