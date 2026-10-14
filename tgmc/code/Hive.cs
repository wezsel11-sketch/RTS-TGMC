#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Activities;
using OpenRA.Mods.Common.Activities;
using OpenRA.Mods.Common.Orders;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common;
using OpenRA.Primitives;
using OpenRA.Traits;

// Hive tunnels, and the hive power that calls xenos up out of the ground.
namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("A tunnel mouth. Two tunnels of the same hive are paired in the order they were built; a xeno ordered into one comes out of the other.")]
	public class HiveTunnelInfo : TraitInfo
	{
		public override object Create(ActorInitializer init) { return new HiveTunnel(init.Self); }
	}

	public class HiveTunnel : INotifyAddedToWorld, INotifyKilled, INotifyActorDisposing
	{
		readonly Actor self;
		Actor partner;

		public HiveTunnel(Actor self) { this.self = self; }

		// The other end, if it is still standing.
		public Actor Partner => partner != null && partner.IsInWorld && !partner.IsDead ? partner : null;

		void INotifyAddedToWorld.AddedToWorld(Actor self)
		{
			// Pair with the oldest tunnel of the same owner that has no partner yet.
			foreach (var other in self.World.ActorsWithTrait<HiveTunnel>().Where(x => x.Actor != self && x.Actor.Owner == self.Owner)
				.OrderBy(x => x.Actor.ActorID))
			{
				if (other.Actor.IsDead || other.Trait.Partner != null)
					continue;

				partner = other.Actor;
				other.Trait.partner = self;
				break;
			}
		}

		void Unlink()
		{
			if (partner != null && partner.TraitOrDefault<HiveTunnel>() is { } other && other.partner == self)
				other.partner = null;

			partner = null;
		}

		void INotifyKilled.Killed(Actor self, AttackInfo e) { Unlink(); }

		void INotifyActorDisposing.Disposing(Actor self) { Unlink(); }
	}

	[Desc("Lets the unit walk into a paired hive tunnel and come out of the other end. Right-click one of the hive's tunnels.")]
	public class UsesHiveTunnelsInfo : TraitInfo
	{
		[Desc("Ticks spent underground between the two mouths.")]
		public readonly int Delay = 20;

		[CursorReference]
		public readonly string Cursor = "enter";

		public readonly string Image = "fx-infest";
		public readonly string Sequence = "evolve";
		public readonly string Palette = "effect";
		public readonly string[] Sounds = [];

		public override object Create(ActorInitializer init) { return new UsesHiveTunnels(this); }
	}

	public class UsesHiveTunnels : IIssueOrder, IResolveOrder
	{
		public readonly UsesHiveTunnelsInfo Info;

		public UsesHiveTunnels(UsesHiveTunnelsInfo info) { Info = info; }

		IEnumerable<IOrderTargeter> IIssueOrder.Orders
		{
			get { yield return new TunnelTargeter(Info.Cursor); }
		}

		Order IIssueOrder.IssueOrder(Actor self, IOrderTargeter order, in Target target, bool queued)
		{
			return order.OrderID == "EnterHiveTunnel" ? new Order(order.OrderID, self, target, queued) : null;
		}

		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (order.OrderString != "EnterHiveTunnel" || order.Target.Type != TargetType.Actor)
				return;

			var tunnel = order.Target.Actor;
			if (tunnel.TraitOrDefault<HiveTunnel>()?.Partner == null)
				return;

			if (!order.Queued)
				self.CancelActivity();

			self.QueueActivity(order.Queued, new UseHiveTunnel(self, tunnel, Info));
			self.ShowTargetLines();
		}

		sealed class TunnelTargeter : UnitOrderTargeter
		{
			public TunnelTargeter(string cursor)
				: base("EnterHiveTunnel", 7, cursor, false, true) { }

			public override bool CanTargetActor(Actor self, Actor target, TargetModifiers modifiers, ref string cursor)
			{
				return target.Owner == self.Owner && target.TraitOrDefault<HiveTunnel>()?.Partner != null;
			}

			public override bool CanTargetFrozenActor(Actor self, FrozenActor target, TargetModifiers modifiers, ref string cursor)
			{
				return false;
			}
		}
	}

	sealed class UseHiveTunnel : Activity
	{
		readonly Actor tunnel;
		readonly UsesHiveTunnelsInfo info;
		bool walking;
		int wait;

		public UseHiveTunnel(Actor self, Actor tunnel, UsesHiveTunnelsInfo info)
		{
			this.tunnel = tunnel;
			this.info = info;
			wait = info.Delay;
		}

		public override bool Tick(Actor self)
		{
			var partner = tunnel.IsInWorld && !tunnel.IsDead ? tunnel.TraitOrDefault<HiveTunnel>()?.Partner : null;
			if (IsCanceling || partner == null)
				return true;

			// The base class has run the walk to the mouth before this is called again.
			if (!walking)
			{
				walking = true;
				QueueChild(new MoveAdjacentTo(self, Target.FromActor(tunnel)));
				return false;
			}

			if (--wait > 0)
				return false;

			var mobile = self.TraitOrDefault<Mobile>();
			if (mobile == null)
				return true;

			var world = self.World;
			var exit = mobile.NearestMoveableCell(partner.Location);
			Fx.Sprite(world, self.CenterPosition, info.Image, info.Sequence, info.Palette);
			Fx.Sound(world, self.CenterPosition, info.Sounds);
			mobile.SetPosition(self, exit);
			mobile.SetCenterPosition(self, world.Map.CenterOfCell(exit));
			Fx.Sprite(world, self.CenterPosition, info.Image, info.Sequence, info.Palette);
			Fx.Sound(world, self.CenterPosition, info.Sounds);
			return true;
		}
	}

	[Desc("Hive power: a group of xenos bursts out of the ground around the spot you pick.")]
	public class CallOfTheBurrowedPowerInfo : SupportPowerInfo
	{
		[ActorReference]
		[Desc("The xenos that come up. They belong to the player who calls them.")]
		public readonly string[] Actors = [];

		[Desc("Cells around the target they are spread over.")]
		public readonly int Radius = 3;

		public readonly string Image = "fx-infest";
		public readonly string Sequence = "evolve";
		public readonly string Palette = "effect";
		public readonly string[] Sounds = [];

		public override object Create(ActorInitializer init) { return new CallOfTheBurrowedPower(init.Self, this); }
	}

	public class CallOfTheBurrowedPower : SupportPower
	{
		readonly CallOfTheBurrowedPowerInfo info;

		public CallOfTheBurrowedPower(Actor self, CallOfTheBurrowedPowerInfo info)
			: base(self, info)
		{
			this.info = info;
		}

		public override void Activate(Actor self, Order order, SupportPowerManager manager)
		{
			base.Activate(self, order, manager);

			var world = self.World;
			var centre = world.Map.CellContaining(order.Target.CenterPosition);
			var cells = world.Map.FindTilesInCircle(centre, info.Radius).OrderBy(c => (c - centre).LengthSquared).ToList();
			var used = new HashSet<CPos>();
			var owner = self.Owner;

			Fx.Sound(world, order.Target.CenterPosition, info.Sounds);
			foreach (var type in info.Actors)
			{
				var mobile = world.Map.Rules.Actors[type].TraitInfoOrDefault<MobileInfo>();
				var cell = cells.FirstOrDefault(c => !used.Contains(c) && (mobile == null || mobile.CanEnterCell(world, null, c)));
				if (cell == default)
					continue;

				used.Add(cell);
				var spawn = type;
				world.AddFrameEndTask(w =>
				{
					Fx.Sprite(w, w.Map.CenterOfCell(cell), info.Image, info.Sequence, info.Palette);
					w.CreateActor(spawn, new TypeDictionary
					{
						new LocationInit(cell),
						new OwnerInit(owner),
						new FactionInit(owner.Faction.InternalName)
					});
				});
			}
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using OpenRA.Mods.TGMC.Traits;
	using OpenRA.Scripting;

	[ScriptPropertyGroup("General")]
	public class HiveTunnelProperties : ScriptActorProperties, Requires<UsesHiveTunnelsInfo>
	{
		public HiveTunnelProperties(ScriptContext context, Actor self)
			: base(context, self) { }

		[Desc("Walk into the given hive tunnel and come out of its partner, as a right-click on the tunnel does.")]
		public void EnterHiveTunnel(Actor tunnel)
		{
			Self.World.IssueOrder(new Order("EnterHiveTunnel", Self, Target.FromActor(tunnel), false));
		}
	}
}
