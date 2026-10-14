#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Effects;
using OpenRA.Graphics;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
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
}
