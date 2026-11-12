#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Effects;
using OpenRA.Graphics;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Traits.Render;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Slowly grows weeds on free cells around this actor, out to MaxRadius, for free. Weeds extend the xeno build area.")]
	public class SpreadWeedsInfo : TraitInfo, Requires<BuildingInfo>
	{
		[ActorReference]
		[Desc("Actor created on each new cell.")]
		public readonly string Actor = "weeds";

		[Desc("Ticks between growth attempts.")]
		public readonly int Interval = 100;

		[Desc("Farthest cell, counted in a square around the actor, that weeds will reach.")]
		public readonly int MaxRadius = 3;

		[Desc("Random cells tried each time before the reach grows by one.")]
		public readonly int Attempts = 6;

		public override object Create(ActorInitializer init) { return new SpreadWeeds(this); }
	}

	public class SpreadWeeds : ITick, INotifyKilled, INotifyRemovedFromWorld
	{
		readonly System.Collections.Generic.List<Actor> grown = new();
		int withering;
		readonly SpreadWeedsInfo info;
		int countdown;
		int reach = 1;

		public SpreadWeeds(SpreadWeedsInfo info)
		{
			this.info = info;
			countdown = info.Interval;
		}

		// When the node dies, the weeds it grew wither away one by one. Marines shoot the node, not the weeds.
		void INotifyKilled.Killed(Actor self, AttackInfo e)
		{
			Wither(self);
		}

		void INotifyRemovedFromWorld.RemovedFromWorld(Actor self)
		{
			Wither(self);
		}

		void Wither(Actor self)
		{
			if (withering > 0 || grown.Count == 0)
				return;

			withering = 1;
			var weeds = grown.ToArray();
			grown.Clear();
			self.World.AddFrameEndTask(w => w.Add(new WeedsWither(weeds, self.World.SharedRandom)));
		}

		void ITick.Tick(Actor self)
		{
			if (--countdown > 0)
				return;

			countdown = info.Interval;

			var world = self.World;
			var ai = world.Map.Rules.Actors[info.Actor];
			var bi = ai.TraitInfo<BuildingInfo>();
			var rng = world.SharedRandom;

			for (var i = 0; i < info.Attempts; i++)
			{
				var cell = self.Location + new CVec(rng.Next(-reach, reach + 1), rng.Next(-reach, reach + 1));
				if (!world.CanPlaceBuilding(cell, ai, bi, null))
					continue;

				var owner = self.Owner;
				world.AddFrameEndTask(w =>
				{
					// The cell may have been taken since the check above.
					if (self.IsDead || !w.CanPlaceBuilding(cell, ai, bi, null))
						return;

					grown.Add(w.CreateActor(info.Actor, new TypeDictionary
					{
						new LocationInit(cell),
						new OwnerInit(owner),
						new FactionInit(owner.Faction.InternalName)
					}));
				});

				return;
			}

			// Nothing free within reach: grow the reach.
			if (reach < info.MaxRadius)
				reach++;
		}
	}

	// Kills the weeds of a dead node a few at a time, about five seconds from start to finish.
	sealed class WeedsWither : IEffect
	{
		readonly System.Collections.Generic.List<Actor> left;
		readonly OpenRA.Support.MersenneTwister rng;
		int ticks;

		public WeedsWither(Actor[] weeds, OpenRA.Support.MersenneTwister rng)
		{
			left = new System.Collections.Generic.List<Actor>(weeds);
			this.rng = rng;
		}

		public void Tick(World world)
		{
			if (++ticks % 4 != 0)
				return;

			for (var i = 0; i < 2 && left.Count > 0; i++)
			{
				var k = rng.Next(left.Count);
				var weed = left[k];
				left.RemoveAt(k);
				if (!weed.IsDead && !weed.Disposed)
					weed.Kill(weed);
			}

			if (left.Count == 0)
				world.AddFrameEndTask(w => w.Remove(this));
		}

		public System.Collections.Generic.IEnumerable<IRenderable> Render(WorldRenderer wr)
		{
			yield break;
		}
	}

	[Desc("A weed cell that joins its neighbours: its sprite is ragged on each side with no weed beyond it.")]
	public class WeedEdgesInfo : TraitInfo
	{
		[Desc("The sequence for a set of joined sides is this plus a number: 1 north, 2 south, 4 east, 8 west, added up. " +
			"Empty for an actor that only counts as a neighbour.")]
		public readonly string Prefix = "c";

		[Desc("Draw the carpet under the actor from this image, and leave its own body alone (a weed node, whose body is the sack). " +
			"Empty, or the actor's own image: the carpet is the actor's body.")]
		public readonly string Image = null;

		public override object Create(ActorInitializer init) { return new WeedEdges(this); }
	}

	public class WeedEdges : INotifyCreated, INotifyAddedToWorld, INotifyRemovedFromWorld
	{
		static readonly (CVec Offset, int Bit)[] Sides = [(new CVec(0, -1), 1), (new CVec(0, 1), 2), (new CVec(1, 0), 4), (new CVec(-1, 0), 8)];
		readonly WeedEdgesInfo info;

		Animation carpet;

		public WeedEdges(WeedEdgesInfo info) { this.info = info; }

		void INotifyCreated.Created(Actor self)
		{
			// An actor that inherits this trait cannot clear Image in yaml (an empty value keeps the inherited one).
			var rs = self.Trait<RenderSprites>();
			if (string.IsNullOrEmpty(info.Image) || info.Image == rs.GetImage(self))
				return;

			carpet = new Animation(self.World, info.Image);
			carpet.PlayRepeating(info.Prefix + 0);
			rs.Add(new AnimationWithOffset(carpet, null, null));
		}

		static WeedEdges At(Actor self, CPos cell, out Actor other)
		{
			// Weeds can be walked on, so the actor map does not hold them; the building influence does.
			foreach (var a in self.World.WorldActor.Trait<BuildingInfluence>().GetBuildingsAt(cell))
			{
				var edges = a == self || a.IsDead ? null : a.TraitOrDefault<WeedEdges>();
				if (edges != null)
				{
					other = a;
					return edges;
				}
			}

			other = null;
			return null;
		}

		void Refresh(Actor self, CPos? without)
		{
			if (string.IsNullOrEmpty(info.Prefix) || !self.IsInWorld)
				return;

			var joined = 0;
			foreach (var (offset, bit) in Sides)
				if (self.Location + offset != without && At(self, self.Location + offset, out _) != null)
					joined |= bit;

			(carpet ?? self.Trait<WithSpriteBody>().DefaultAnimation).PlayRepeating(info.Prefix + joined);
		}

		void RefreshAround(Actor self, CPos? without)
		{
			foreach (var (offset, _) in Sides)
				At(self, self.Location + offset, out var other)?.Refresh(other, without);
		}

		void INotifyAddedToWorld.AddedToWorld(Actor self)
		{
			// Look once every actor added this tick is in place.
			self.World.AddFrameEndTask(_ =>
			{
				Refresh(self, null);
				RefreshAround(self, null);
			});
		}

		void INotifyRemovedFromWorld.RemovedFromWorld(Actor self) { RefreshAround(self, self.Location); }
	}
}
