using System.Linq;
using OpenRA.Mods.Common.Activities;
using OpenRA.Mods.Common.Traits;
using OpenRA.Scripting;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	/// <summary>Marks a structure that friendly units can retreat to.</summary>
	public class ReturnPointInfo : TraitInfo
	{
		public override object Create(ActorInitializer init) { return new ReturnPoint(); }
	}

	public class ReturnPoint { }

	[Desc("Lets the unit retreat to the nearest friendly return point (the TgmcRetreat order).")]
	public class RetreatInfo : ConditionalTraitInfo
	{
		public override object Create(ActorInitializer init) { return new Retreat(this); }
	}

	public class Retreat : ConditionalTrait<RetreatInfo>, IResolveOrder
	{
		public const string OrderName = "TgmcRetreat";

		public Retreat(RetreatInfo info)
			: base(info) { }

		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (order.OrderString == OrderName)
				Issue(self, order.Queued);
		}

		/// <summary>Moves the unit to the nearest friendly return point. Returns false, with no change, when there is none.</summary>
		public bool Issue(Actor self, bool queued)
		{
			if (IsTraitDisabled)
				return false;

			var point = NearestReturnPoint(self);
			if (point == null)
				return false;

			self.QueueActivity(queued, new Move(self, point.Location));
			return true;
		}

		static Actor NearestReturnPoint(Actor self)
		{
			return self.World.ActorsWithTrait<ReturnPoint>()
				.Where(p => !p.Actor.IsDead && p.Actor.Owner.RelationshipWith(self.Owner) == PlayerRelationship.Ally)
				.Select(p => p.Actor)
				.OrderBy(a => (a.CenterPosition - self.CenterPosition).LengthSquared)
				.FirstOrDefault();
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using OpenRA.Mods.TGMC.Traits;

	[ScriptPropertyGroup("Combat")]
	public class RetreatProperties : ScriptActorProperties, Requires<RetreatInfo>
	{
		public RetreatProperties(ScriptContext context, Actor self)
			: base(context, self) { }

		[Desc("Retreat to the nearest friendly return point, as the TgmcRetreat button does. Returns false, and does nothing, if there is none.")]
		public bool Retreat()
		{
			var trait = Self.TraitsImplementing<OpenRA.Mods.TGMC.Traits.Retreat>().FirstOrDefault();
			return trait != null && trait.Issue(Self, false);
		}
	}
}
