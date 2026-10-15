#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Effects;
using OpenRA.GameRules;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Projectiles;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Projectiles
{
	[Desc("A lobbed bullet (mortar, howitzer, rocket) that also whistles on its way down: the sound plays at the target spot shortly before the impact.")]
	public class ShellInfo : BulletInfo
	{
		[Desc("Sounds played at the target while the shell is in the air, one picked at random.")]
		public readonly string[] WhistleSounds = [];

		[Desc("How many ticks before the impact the whistle starts. A shell that flies for less than this whistles at once.")]
		public readonly int WhistleLead = 50;

		public override IProjectile Create(ProjectileArgs args)
		{
			var world = args.SourceActor.World;
			if (WhistleSounds.Length > 0)
			{
				var speed = Speed[0].Length;
				var distance = (args.PassiveTarget - args.Source).HorizontalLength;
				var flight = speed > 0 ? distance / speed : 0;
				world.AddFrameEndTask(w => w.Add(new Whistle(args.PassiveTarget, WhistleSounds, System.Math.Max(0, flight - WhistleLead))));
			}

			return base.Create(args);
		}
	}

	[Desc("A bullet that stops at cover: a wall (rock, plain or reinforced) or an object with BlocksBullets between the gun and the target takes the hit instead, " +
		"at the cell where it was stopped. Shooters see through walls, so without this they would shoot straight through them.")]
	public class CoverBulletInfo : BulletInfo
	{
		public override IProjectile Create(ProjectileArgs args)
		{
			var world = args.SourceActor.World;
			var stop = Stop(world, args.Source, args.PassiveTarget);
			if (stop != null)
				args.PassiveTarget = stop.Value;

			return base.Create(args);
		}

		static WPos? Stop(World world, WPos from, WPos to)
		{
			var map = world.Map;
			var line = to - from;
			var length = line.HorizontalLength;
			if (length < 1024)
				return null;

			var start = map.CellContaining(from);
			var end = map.CellContaining(to);
			var steps = length / 400;
			var last = start;
			var before = from;
			for (var i = 1; i < steps; i++)
			{
				var point = from + line * i / steps;
				var cell = map.CellContaining(point);
				if (cell == last || cell == start || cell == end)
				{
					before = point;
					continue;
				}

				last = cell;
				if (!map.Contains(cell))
					return before;

				if (map.GetTerrainInfo(cell).Type is "Rock" or "Wall" or "ReinforcedWall")
					return before;

				foreach (var a in world.ActorMap.GetActorsAt(cell))
				{
					if (a.IsDead)
						continue;

					var cover = a.Info.TraitInfoOrDefault<BlocksBulletsInfo>();
					if (cover != null && cover.Stops(world, a, from))
						return map.CenterOfCell(cell);
				}

				before = point;
			}

			return null;
		}
	}

	[Desc("Cover: a CoverBullet stops at this actor (a barricade, a closet, a window...), and hits it. A barricade has a front (FaceX, FaceY, in cells): " +
		"shots from the front side are mostly caught (FrontBlock percent), shots from behind or the flanks pass over it.")]
	public class BlocksBulletsInfo : TraitInfo
	{
		[Desc("The side the cover faces, as a direction on the map. 0, 0 for cover that protects all around.")]
		public readonly int FaceX = 0;
		public readonly int FaceY = 0;

		[Desc("Chance in percent that a shot from the front is stopped (the rest are only off target by the cover). Cover without a front always stops.")]
		public readonly int FrontBlock = 70;

		public bool Stops(World world, Actor self, WPos shooter)
		{
			if (FaceX == 0 && FaceY == 0)
				return true;

			var offset = shooter - self.CenterPosition;
			var front = (long)offset.X * FaceX + (long)offset.Y * FaceY > 0;
			return front && world.SharedRandom.Next(100) < FrontBlock;
		}

		public override object Create(ActorInitializer init) { return new BlocksBullets(); }
	}

	public class BlocksBullets { }

	sealed class Whistle : IEffect
	{
		readonly WPos pos;
		readonly string[] sounds;
		int delay;

		public Whistle(WPos pos, string[] sounds, int delay)
		{
			this.pos = pos;
			this.sounds = sounds;
			this.delay = delay;
		}

		public void Tick(World world)
		{
			if (delay-- > 0)
				return;

			Fx.Sound(world, pos, sounds);
			world.AddFrameEndTask(w => w.Remove(this));
		}

		public System.Collections.Generic.IEnumerable<IRenderable> Render(WorldRenderer wr)
		{
			yield break;
		}
	}
}
