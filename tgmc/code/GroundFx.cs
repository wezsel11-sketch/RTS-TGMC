#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Effects;
using OpenRA.GameRules;
using OpenRA.Mods.Common;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.World)]
	[Desc("TGMC's weather: one of its animated 32 px weather tiles (rain, acid rain, ash, snow, dust) drawn over every cell on screen. " +
		"The lobby's Weather option grants the condition that switches an instance on (TgmcOptions in Options.cs).")]
	public class TiledWeatherInfo : ConditionalTraitInfo
	{
		public readonly string Image = "fx-weather";

		[SequenceReference(nameof(Image))]
		public readonly string Sequence = "rain";

		[PaletteReference]
		public readonly string Palette = "effect";

		[Desc("How see-through the weather is, 0 to 1.")]
		public readonly float Alpha = 0.6f;

		public override object Create(ActorInitializer init) { return new TiledWeather(this); }
	}

	public class TiledWeather : ConditionalTrait<TiledWeatherInfo>, IRenderAboveShroud, ITick, IWorldLoaded
	{
		Animation anim;

		public TiledWeather(TiledWeatherInfo info)
			: base(info) { }

		void IWorldLoaded.WorldLoaded(World w, WorldRenderer wr)
		{
			anim = new Animation(w, Info.Image);
			anim.PlayRepeating(Info.Sequence);
		}

		void ITick.Tick(Actor self)
		{
			if (!IsTraitDisabled)
				anim?.Tick();
		}

		bool IRenderAboveShroud.SpatiallyPartitionable => false;

		IEnumerable<IRenderable> IRenderAboveShroud.RenderAboveShroud(Actor self, WorldRenderer wr)
		{
			if (IsTraitDisabled || anim == null)
				yield break;

			var map = self.World.Map;
			var sprite = anim.Image;
			var palette = wr.Palette(Info.Palette);
			foreach (var puv in wr.Viewport.AllVisibleCells)
			{
				var cell = ((MPos)puv).ToCPos(map);
				yield return new SpriteRenderable(sprite, map.CenterOfCell(cell), WVec.Zero, 0, palette, 1f, Info.Alpha,
					System.Numerics.Vector3.One, TintModifiers.IgnoreWorldTint, true);
			}
		}
	}

	[Desc("Leaves bloody footprints behind (fluidtracks.dmi) while badly hurt and on the move: one every StepCells cells, facing the " +
		"way the unit walks. They lie a while, then fade.")]
	public class LeavesTracksInfo : TraitInfo, Requires<IHealthInfo>
	{
		public readonly string Image = "fx-tracks";

		[SequenceReference(nameof(Image))]
		[Desc("Sequences picked by turns, one per step.")]
		public readonly string[] Sequences = ["human1", "human2"];

		[PaletteReference]
		public readonly string Palette = "effect";

		[Desc("Only at or below this share of full health (percent).")]
		public readonly int HealthPercent = 40;

		public readonly int StepCells = 1;

		public readonly int Linger = 400;
		public readonly int Fade = 150;

		public override object Create(ActorInitializer init) { return new LeavesTracks(init.Self, this); }
	}

	public class LeavesTracks : ITick
	{
		readonly LeavesTracksInfo info;
		readonly IHealth health;
		CPos last;
		bool started;
		int step;

		public LeavesTracks(Actor self, LeavesTracksInfo info)
		{
			this.info = info;
			health = self.Trait<IHealth>();
		}

		void ITick.Tick(Actor self)
		{
			if (!self.IsInWorld || health.IsDead)
				return;

			var here = self.Location;
			if (!started || health.HP * 100 > health.MaxHP * info.HealthPercent)
			{
				started = true;
				last = here;
				return;
			}

			var moved = here - last;
			if (Math.Max(Math.Abs(moved.X), Math.Abs(moved.Y)) < info.StepCells)
				return;

			var facing = new WVec(moved.X * 1024, moved.Y * 1024, 0).Yaw;
			var sequence = info.Sequences[step++ % info.Sequences.Length];
			var pos = self.World.Map.CenterOfCell(last);
			self.World.AddFrameEndTask(w => w.Add(new Decal(w, pos, info.Image, sequence, info.Palette, facing, info.Linger, info.Fade)));
			last = here;
		}
	}

	/// <summary>A still picture on the ground (a footprint, a bullet hole) that lies for Linger ticks and fades out over Fade.</summary>
	sealed class Decal : IEffect
	{
		readonly WPos pos;
		readonly Animation anim;
		readonly string palette;
		readonly int linger;
		readonly int fade;
		readonly int zOffset;
		int age;

		// zOffset below 0 lies under the units (footprints, above weeds and blood, see GROUND_Z in mod/build_sprites.py); above 0 sits on top of the structure it marks (holes).
		public Decal(World world, WPos pos, string image, string sequence, string palette, WAngle facing, int linger, int fade, int zOffset = -14500)
		{
			this.zOffset = zOffset;
			this.pos = pos;
			this.palette = palette;
			this.linger = linger;
			this.fade = fade;
			anim = new Animation(world, image, () => facing);
			anim.PlayRepeating(sequence);
		}

		public void Tick(World world)
		{
			if (++age > linger + fade)
				world.AddFrameEndTask(w => w.Remove(this));
		}

		public IEnumerable<IRenderable> Render(WorldRenderer wr)
		{
			var faded = age - linger;
			var alpha = faded > 0 ? Math.Max(0f, 1f - faded / (float)Math.Max(1, fade)) : 1f;
			return anim.Render(pos, WVec.Zero, zOffset, wr.Palette(palette)).Select(r => r is IModifyableRenderable m ? m.WithAlpha(alpha) : r);
		}
	}

	/// <summary>A blinking ground marker: where something is about to land. Removed after its duration.</summary>
	sealed class Marker : IEffect
	{
		readonly WPos pos;
		readonly Animation anim;
		readonly string palette;
		readonly int duration;
		int age;

		public Marker(World world, WPos pos, string image, string sequence, string palette, int duration)
		{
			this.pos = pos;
			this.palette = palette;
			this.duration = duration;
			anim = new Animation(world, image);
			anim.PlayRepeating(sequence);
		}

		public void Tick(World world)
		{
			if (++age >= duration)
				world.AddFrameEndTask(w => w.Remove(this));
		}

		public IEnumerable<IRenderable> Render(WorldRenderer wr)
		{
			// Pulses between half and full strength, faster as the moment comes.
			var speed = age > duration * 2 / 3 ? 4 : 8;
			var alpha = 0.5f + 0.5f * (age / speed % 2);
			return anim.Render(pos, WVec.Zero, -511, wr.Palette(palette)).Select(r => r is IModifyableRenderable m ? m.WithAlpha(alpha) : r);
		}
	}

	public static class GroundFx
	{
		/// <summary>Shows a blinking marker at the spot for the given ticks.</summary>
		public static void Marker(World world, WPos pos, string image, string sequence, int ticks, string palette = "effect")
		{
			if (ticks > 0)
				world.AddFrameEndTask(w => w.Add(new Marker(w, pos, image, sequence, palette, ticks)));
		}

		internal static void AddDecal(World world, WPos pos, string image, string sequence, string palette, int linger, int fade)
		{
			world.AddFrameEndTask(w => w.Add(new Decal(w, pos, image, sequence, palette, WAngle.Zero, linger, fade, 1024)));
		}
	}
}

namespace OpenRA.Mods.TGMC.Warheads
{
	using OpenRA.Mods.TGMC.Traits;

	[Desc("Leaves a mark on a structure it hits (bullet holes, acid holes) that lies a while and then fades. Only actors that match " +
		"ValidTargets get one; a mark lands somewhere on the structure, not always on its centre.")]
	public class DecalWarhead : Warhead
	{
		public readonly string Image = "fx-hole";

		[SequenceReference(nameof(Image))]
		[Desc("One is picked at random per hit.")]
		public readonly string[] Sequences = [];

		[PaletteReference]
		public readonly string Palette = "effect";

		[Desc("Chance (percent) that a hit leaves a mark.")]
		public readonly int Chance = 35;

		[Desc("How far from the centre a mark may land.")]
		public readonly WDist Scatter = new(384);

		public readonly int Linger = 300;
		public readonly int Fade = 100;

		public override void DoImpact(in Target target, WarheadArgs args)
		{
			if (target.Type == TargetType.Invalid || Sequences.Length == 0)
				return;

			// A bullet may hit a spot rather than an actor: the structure standing there counts.
			var firedBy = args.SourceActor;
			var victim = target.Type == TargetType.Actor ? target.Actor
				: firedBy.World.FindActorsOnCircle(target.CenterPosition, new WDist(512))
					.FirstOrDefault(a => !a.IsDead && IsValidAgainst(a, firedBy));
			if (victim == null || victim.IsDead || !IsValidAgainst(victim, firedBy))
				return;

			// Looks only: the local random keeps the shared game state out of it.
			var random = victim.World.LocalRandom;
			if (random.Next(100) >= Chance)
				return;

			var r = Scatter.Length;
			var pos = victim.CenterPosition + new WVec(random.Next(-r, r + 1), random.Next(-r, r + 1), 0);
			GroundFx.AddDecal(victim.World, pos, Image, Sequences[random.Next(Sequences.Length)], Palette, Linger, Fade);
		}
	}
}
