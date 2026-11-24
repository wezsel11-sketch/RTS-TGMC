using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("One end of the wraith's portal. The two ends its owner made on the same tick are a pair: a unit of either side that walks " +
		"onto one end comes out at the other and stops there. It goes through again only after it has stepped off.")]
	public class PortalInfo : TraitInfo
	{
		[Desc("How near a unit must come.")]
		public readonly WDist Radius = new(640);

		public readonly string[] Sounds = [];

		public override object Create(ActorInitializer init) { return new Portal(this); }
	}

	public class Portal : ITick, INotifyAddedToWorld
	{
		readonly PortalInfo info;

		// Units standing on this end now: only one that was not here at the last look goes through.
		HashSet<Actor> inside = [];
		int born;
		bool primed;
		Actor partner;

		public Portal(PortalInfo info) { this.info = info; }

		void INotifyAddedToWorld.AddedToWorld(Actor self) { born = self.World.WorldTick; }

		void ITick.Tick(Actor self)
		{
			var world = self.World;
			if (world.WorldTick % 3 != 0)
				return;

			// shortcut: two wraiths of one player opening portals on the same tick would mix their ends; give each pair an id if that shows.
			if (partner == null || partner.IsDead || !partner.IsInWorld)
				partner = world.ActorsWithTrait<Portal>()
					.FirstOrDefault(p => p.Actor != self && p.Actor.Owner == self.Owner && p.Trait.born == born && p.Actor.IsInWorld).Actor;

			var here = world.FindActorsInCircle(self.CenterPosition, info.Radius)
				.Where(a => !a.IsDead && a.IsInWorld && a.Info.HasTraitInfo<MobileInfo>()).ToHashSet();
			// Whoever stands here when the portal opens (the wraith itself) stays: only a unit that walks in goes through.
			if (!primed)
			{
				primed = true;
				inside = here;
				return;
			}

			if (partner != null)
			{
				var far = partner.Trait<Portal>();
				foreach (var a in here.Where(a => !inside.Contains(a)).ToList())
				{
					var body = a.Trait<IPositionable>();
					var cell = world.Map.FindTilesInCircle(partner.Location, 1).OrderBy(c => (c - partner.Location).LengthSquared)
						.FirstOrDefault(c => body.CanEnterCell(c));
					if (cell == default)
						continue;

					// SimpleTeleport waits for the step under way to end: a bare SetPosition is undone by the move still drawing it
					// along its old path. It stays in `inside` here until it is gone, so the wait does not send it twice.
					a.QueueActivity(false, new OpenRA.Mods.Common.Activities.SimpleTeleport(cell));
					far.inside.Add(a);
					Fx.Sound(world, self.CenterPosition, info.Sounds);
				}
			}

			inside = here;
		}
	}
}
