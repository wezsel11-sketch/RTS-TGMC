#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Attach to the world actor. Eases the camera toward where scrolling pushed it, instead of jumping.")]
	public class SmoothScrollInfo : TraitInfo
	{
		[Desc("Fraction of the remaining distance covered each frame.")]
		public readonly float Rate = 0.2f;

		[Desc("A single frame's move bigger than this many pixels counts as a jump (minimap click, jump-to-base) and is not eased.")]
		public readonly int JumpDistance = 600;

		public override object Create(ActorInitializer init) { return new SmoothScroll(this); }
	}

	public class SmoothScroll : IWorldLoaded
	{
		readonly SmoothScrollInfo info;
		Viewport viewport;
		int2 last;
		Vector2 pending;

		public SmoothScroll(SmoothScrollInfo info) { this.info = info; }

		void IWorldLoaded.WorldLoaded(World w, WorldRenderer wr)
		{
			viewport = wr.Viewport;
			last = viewport.TopLeft;
			viewport.ViewportTick += Tick;
		}

		// Runs after the engine's viewport widget has moved the camera this frame: undo that move, bank it, and play a share of it back.
		void Tick()
		{
			var now = viewport.TopLeft;
			var moved = (now - last).ToVector2();

			if (moved.Length() > info.JumpDistance)
			{
				pending = Vector2.Zero;
				last = now;
				return;
			}

			if (moved != Vector2.Zero)
			{
				viewport.Scroll(-moved, false);
				pending += moved;
			}

			if (pending.LengthSquared() < 1f)
			{
				pending = Vector2.Zero;
				last = viewport.TopLeft;
				return;
			}

			var step = pending * info.Rate;
			if (step.Length() < 1f)
				step = pending;

			var before = viewport.TopLeft;
			viewport.Scroll(step, false);
			var got = (viewport.TopLeft - before).ToVector2();

			// Stopped by the map border: drop what is left so the camera does not creep.
			pending = got.Length() < step.Length() * 0.5f ? Vector2.Zero : pending - step;
			last = viewport.TopLeft;
		}
	}

	[Desc("Idle units that stand too close to a friendly idle unit step to a free cell further from it.")]
	public class SpreadOutInfo : TraitInfo, Requires<MobileInfo>
	{
		[Desc("A friendly idle unit closer than this makes the unit step away.")]
		public readonly WDist TooClose = WDist.FromCells(1);

		[Desc("Ticks between checks while idle.")]
		public readonly int Interval = 20;

		[Desc("How many cells away a unit may step to find room.")]
		public readonly int SearchRadius = 2;

		public override object Create(ActorInitializer init) { return new SpreadOut(init.Self, this); }
	}

	public class SpreadOut : INotifyIdle
	{
		readonly SpreadOutInfo info;
		readonly Mobile mobile;
		int countdown;

		public SpreadOut(Actor self, SpreadOutInfo info)
		{
			this.info = info;
			mobile = self.Trait<Mobile>();
		}

		void INotifyIdle.TickIdle(Actor self)
		{
			if (--countdown > 0)
				return;

			countdown = info.Interval;

			var neighbours = self.World.FindActorsInCircle(self.CenterPosition, info.TooClose)
				.Where(a => a != self && a.IsIdle && a.Owner.IsAlliedWith(self.Owner) && a.Info.HasTraitInfo<SpreadOutInfo>())
				.ToList();

			if (neighbours.Count == 0)
				return;

			var here = Score(self, self.Location, neighbours);
			var best = self.Location;
			var bestScore = here;

			for (var dx = -info.SearchRadius; dx <= info.SearchRadius; dx++)
			{
				for (var dy = -info.SearchRadius; dy <= info.SearchRadius; dy++)
				{
					var cell = self.Location + new CVec(dx, dy);
					if (cell == self.Location || !mobile.CanEnterCell(cell))
						continue;

					var score = Score(self, cell, neighbours);
					if (score > bestScore)
					{
						bestScore = score;
						best = cell;
					}
				}
			}

			if (best != self.Location)
				self.QueueActivity(mobile.MoveTo(best));
		}

		// Distance in world units to the nearest neighbour if the unit stood on this cell.
		static int Score(Actor self, CPos cell, List<Actor> neighbours)
		{
			var pos = self.World.Map.CenterOfCell(cell);
			return neighbours.Min(a => (a.CenterPosition - pos).Length);
		}
	}
}
