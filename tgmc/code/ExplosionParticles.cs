#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Collections.Generic;
using System.Numerics;
using OpenRA.Effects;
using OpenRA.GameRules;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Mods.TGMC.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Warheads
{
	[Desc("One particle system of a blast, after TGMC's explosion (explosions.dm): Count sprites thrown out from the impact, each flying, rising, " +
		"falling back and fading on its own. A blast stacks several of them (smoke, dust, debris, sparks).")]
	public class ExplosionParticlesWarhead : Warhead
	{
		public readonly string Image = null;

		[Desc("Sequences of Image, one picked at random per particle.")]
		public readonly string[] Sequences = ["idle"];

		public readonly string Palette = "effect";

		public readonly int Count = 20;

		[Desc("Radius of the disc the particles start in.")]
		public readonly WDist Spread = WDist.Zero;

		[Desc("Sideways speed, outward in a random direction, in 1/1024 cell per tick (a minimum and a maximum).")]
		public readonly int MinSpeed = 0;
		public readonly int MaxSpeed = 0;

		[Desc("Starting upward speed, in 1/1024 cell per tick (a minimum and a maximum).")]
		public readonly int MinRise = 0;
		public readonly int MaxRise = 0;

		[Desc("Pull downward, in 1/1024 cell per tick every tick.")]
		public readonly int Gravity = 0;

		[Desc("Percent of the sideways speed lost every tick.")]
		public readonly int Friction = 0;

		[Desc("Ticks a particle lives (a minimum and a maximum), the ticks at the start it fades in, and the ticks at the end it fades out.")]
		public readonly int MinLife = 15;
		public readonly int MaxLife = 25;
		public readonly int FadeIn = 0;
		public readonly int FadeOut = 8;

		[Desc("Size of the sprite at the start and at the end of its life, as a multiple of its natural size.")]
		public readonly float StartScale = 1f;
		public readonly float EndScale = 1f;

		[Desc("Colour the sprite is multiplied by, and its opacity.")]
		public readonly Color Tint = Color.White;
		public readonly float Alpha = 1f;

		public override void DoImpact(in Target target, WarheadArgs args)
		{
			if (args.SourceActor == null || target.Type == TargetType.Invalid || string.IsNullOrEmpty(Image))
				return;

			var world = args.SourceActor.World;
			var at = target.CenterPosition;
			world.AddFrameEndTask(w =>
			{
				for (var i = 0; i < Count; i++)
					w.Add(new ExplosionParticle(this, w, at));
			});
		}
	}

	[Desc("Empties the plasma of every xeno within Range of the impact (the plasma-draining orbital warhead's gas). A negative Amount " +
		"gives plasma instead (the queen's Give Plasma).")]
	public class DrainPlasmaWarhead : Warhead
	{
		public readonly WDist Range = new(1536);

		[Desc("Plasma taken from each xeno; negative gives it.")]
		public readonly int Amount = 1000;

		public override void DoImpact(in Target target, WarheadArgs args)
		{
			if (args.SourceActor == null || target.Type == TargetType.Invalid)
				return;

			foreach (var victim in args.SourceActor.World.FindActorsInCircle(target.CenterPosition, Range))
			{
				if (!victim.IsDead && IsValidAgainst(victim, args.SourceActor))
					victim.TraitOrDefault<Plasma>()?.Spend(Amount);
			}
		}
	}

	sealed class ExplosionParticle : IEffect
	{
		readonly ExplosionParticlesWarhead info;
		readonly World world;
		readonly string sequence;
		readonly int life;
		readonly Vector3 tint;
		Vector3 pos;
		Vector3 velocity;
		int age;

		public ExplosionParticle(ExplosionParticlesWarhead info, World world, WPos at)
		{
			this.info = info;
			this.world = world;
			var random = world.LocalRandom;
			sequence = info.Sequences[random.Next(info.Sequences.Length)];
			life = random.Next(info.MinLife, Math.Max(info.MinLife, info.MaxLife) + 1);
			tint = new Vector3(info.Tint.R, info.Tint.G, info.Tint.B) / 255f;

			var angle = random.Next(360) * MathF.PI / 180f;
			var heading = new Vector2(MathF.Cos(angle), MathF.Sin(angle));
			var start = heading * (info.Spread.Length * (random.Next(100) / 100f));
			var speed = random.Next(info.MinSpeed, Math.Max(info.MinSpeed, info.MaxSpeed) + 1);
			pos = new Vector3(at.X + start.X, at.Y + start.Y, at.Z);
			velocity = new Vector3(heading.X * speed, heading.Y * speed, random.Next(info.MinRise, Math.Max(info.MinRise, info.MaxRise) + 1));
		}

		void IEffect.Tick(World w)
		{
			if (++age >= life)
			{
				w.AddFrameEndTask(x => x.Remove(this));
				return;
			}

			pos += velocity;
			var drag = 1f - info.Friction / 100f;
			velocity = new Vector3(velocity.X * drag, velocity.Y * drag, velocity.Z - info.Gravity);

			// A rock that has fallen back to the ground stays there until its life ends, it does not sink.
			if (pos.Z < 0)
			{
				pos.Z = 0;
				velocity = Vector3.Zero;
			}
		}

		IEnumerable<IRenderable> IEffect.Render(WorldRenderer wr)
		{
			var wpos = new WPos((int)pos.X, (int)pos.Y, (int)pos.Z);
			if (world.FogObscures(wpos))
				yield break;

			var sequenceInfo = world.Map.Sequences.GetSequence(info.Image, sequence);
			var t = age / (float)life;
			var scale = (info.StartScale + (info.EndScale - info.StartScale) * t) * sequenceInfo.Scale;
			var alpha = info.Alpha;
			if (info.FadeIn > 0 && age < info.FadeIn)
				alpha *= age / (float)info.FadeIn;
			if (info.FadeOut > 0 && life - age < info.FadeOut)
				alpha *= (life - age) / (float)info.FadeOut;

			yield return new SpriteRenderable(sequenceInfo.GetSprite(0), wpos, WVec.Zero, 1024, wr.Palette(info.Palette), scale, alpha,
				tint, TintModifiers.None, false);
		}
	}
}
