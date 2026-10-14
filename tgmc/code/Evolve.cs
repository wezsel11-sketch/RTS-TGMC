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
	[Desc("Lets the unit morph into another caste. The Deploy key evolves it to Next, Shift + Deploy devolves it to Previous. " +
		"Evolving costs the price difference and needs the next caste's prerequisites. Devolving refunds part of the difference.")]
	public class EvolvesInfo : TraitInfo
	{
		[ActorReference]
		[Desc("Caste this unit evolves into. Empty if it is at the top of its line.")]
		public readonly string Next = null;

		[ActorReference]
		[Desc("Caste this unit devolves into. Empty if it is at the bottom of its line.")]
		public readonly string Previous = null;

		[Desc("Percent of the price difference paid back when devolving.")]
		public readonly int RefundPercent = 50;

		[Desc("Effect image and palette for the morph.")]
		public readonly string Image = "fx-infest";
		public readonly string EvolveSequence = "evolve";
		public readonly string DevolveSequence = "devolve";
		public readonly string Palette = "effect";

		[Desc("Sounds played on evolving and devolving.")]
		public readonly string[] EvolveSounds = [];
		public readonly string[] DevolveSounds = [];

		[Desc("Sound played to the owner when the morph is refused.")]
		public readonly string DenySound = "ui-deny.ogg";

		[FluentReference]
		public readonly string NeedCashMessage = "notification-evolve-cash";

		[FluentReference]
		public readonly string NeedTechMessage = "notification-evolve-tech";

		[CursorReference]
		public readonly string Cursor = "ability";

		[CursorReference]
		public readonly string BlockedCursor = "move-blocked";

		public override object Create(ActorInitializer init) { return new Evolves(init.Self, this); }
	}

	public class Evolves : IIssueOrder, IResolveOrder, IIssueDeployOrder
	{
		readonly EvolvesInfo info;

		public Evolves(Actor self, EvolvesInfo info) { this.info = info; }

		IEnumerable<IOrderTargeter> IIssueOrder.Orders
		{
			get
			{
				if (info.Next != null)
					yield return new DeployOrderTargeter("Evolve", 6, () => info.Cursor);
			}
		}

		Order IIssueOrder.IssueOrder(Actor self, IOrderTargeter order, in Target target, bool queued)
		{
			return order.OrderID == "Evolve" ? new Order("Evolve", self, queued) : null;
		}

		Order IIssueDeployOrder.IssueDeployOrder(Actor self, bool queued)
		{
			return new Order("Evolve", self, queued);
		}

		bool IIssueDeployOrder.CanIssueDeployOrder(Actor self, bool queued)
		{
			return queued ? info.Previous != null : info.Next != null;
		}

		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (order.OrderString != "Evolve")
				return;

			// Shift (queued) means devolve.
			if (order.Queued)
				Morph(self, info.Previous, false);
			else
				Morph(self, info.Next, true);
		}

		public void Evolve(Actor self) { Morph(self, info.Next, true); }

		// Whether an evolve order would go through now, leaving cashReserve behind (the AI asks this before it orders).
		public bool CanEvolve(Actor self, int cashReserve)
		{
			if (info.Next == null || self.IsDead || self.Disposed)
				return false;

			var owner = self.Owner;
			var intoInfo = self.World.Map.Rules.Actors[info.Next];
			var prerequisites = intoInfo.TraitInfoOrDefault<BuildableInfo>()?.Prerequisites ?? [];
			if (!owner.PlayerActor.Trait<TechTree>().HasPrerequisites(prerequisites))
				return false;

			var difference = Price(intoInfo) - Price(self.Info);
			return owner.PlayerActor.Trait<PlayerResources>().GetCashAndResources() >= difference + cashReserve;
		}

		public void Devolve(Actor self) { Morph(self, info.Previous, false); }

		static int Price(ActorInfo ai)
		{
			return ai.TraitInfoOrDefault<ValuedInfo>()?.Cost ?? 0;
		}

		void Morph(Actor self, string into, bool evolving)
		{
			if (into == null || self.IsDead || self.Disposed)
				return;

			var world = self.World;
			var owner = self.Owner;
			var intoInfo = world.Map.Rules.Actors[into];
			var difference = Price(intoInfo) - Price(self.Info);
			var resources = owner.PlayerActor.Trait<PlayerResources>();

			if (evolving)
			{
				var prerequisites = intoInfo.TraitInfoOrDefault<BuildableInfo>()?.Prerequisites ?? [];
				if (!owner.PlayerActor.Trait<TechTree>().HasPrerequisites(prerequisites))
				{
					Refuse(self, info.NeedTechMessage);
					return;
				}

				if (difference > 0 && !resources.TakeCash(difference))
				{
					Refuse(self, info.NeedCashMessage);
					return;
				}
			}
			else if (difference < 0)
			{
				resources.GiveCash(-difference * info.RefundPercent / 100);
			}

			var pos = self.CenterPosition;
			var cell = self.Location;
			var facing = self.TraitOrDefault<IFacing>()?.Facing ?? WAngle.Zero;
			var health = self.TraitOrDefault<IHealth>();
			var fraction = health != null && health.MaxHP > 0 ? health.HP / (float)health.MaxHP : 1f;
			var wasSelected = world.Selection.Contains(self);

			Fx.Sound(world, pos, evolving ? info.EvolveSounds : info.DevolveSounds);
			TgmcEventLog.Post(world, owner, evolving ? "event-evolved" : "event-devolved", pos);
			Fx.Sprite(world, pos, info.Image, evolving ? info.EvolveSequence : info.DevolveSequence, info.Palette);

			world.AddFrameEndTask(w =>
			{
				if (self.IsDead || self.Disposed)
					return;

				self.Dispose();

				var morphed = w.CreateActor(into, new TypeDictionary
				{
					new LocationInit(cell),
					new OwnerInit(owner),
					new FactionInit(owner.Faction.InternalName),
					new FacingInit(facing)
				});

				// Keep the same share of health, so morphing is no free heal.
				var newHealth = morphed.TraitOrDefault<IHealth>();
				if (newHealth != null)
				{
					var missing = newHealth.MaxHP - (int)(newHealth.MaxHP * fraction);
					if (missing > 0)
						morphed.InflictDamage(morphed, new Damage(missing));
				}

				if (wasSelected)
					w.Selection.Add(morphed);
			});
		}

		void Refuse(Actor self, string message)
		{
			Game.Sound.PlayToPlayer(SoundType.UI, self.Owner, info.DenySound);
			TextNotificationsManager.AddTransientLine(self.Owner, message);
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using OpenRA.Mods.TGMC.Traits;

	[ScriptPropertyGroup("General")]
	public class EvolveProperties : ScriptActorProperties, Requires<EvolvesInfo>
	{
		readonly Evolves evolves;

		public EvolveProperties(ScriptContext context, Actor self)
			: base(context, self)
		{
			evolves = self.Trait<Evolves>();
		}

		[Desc("Evolve into the next caste, as the Deploy order does. Costs requisition and needs the caste's prerequisites.")]
		public void Evolve()
		{
			evolves.Evolve(Self);
		}

		[Desc("Devolve into the previous caste, as Shift + Deploy does.")]
		public void Devolve()
		{
			evolves.Devolve(Self);
		}
	}
}
