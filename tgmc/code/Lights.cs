#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Lights up the ground at the muzzle when the unit fires a ranged weapon: a short additive glow (see fx-light in sequences/misc.yaml).")]
	public class MuzzleGlowInfo : TraitInfo
	{
		public readonly string Image = "fx-light";
		public readonly string Sequence = "muzzle";
		public readonly string Palette = "effect";

		[Desc("Weapons that do more than this much damage give a heavy glow (HeavySequence) instead.")]
		public readonly int HeavyDamage = 60;
		public readonly string HeavySequence = "muzzle-heavy";

		[Desc("Weapons that reach no further than this (claws, bites) give no glow.")]
		public readonly WDist MinRange = new(2048);

		public override object Create(ActorInitializer init) { return new MuzzleGlow(this); }
	}

	public class MuzzleGlow : INotifyAttack
	{
		readonly MuzzleGlowInfo info;

		public MuzzleGlow(MuzzleGlowInfo info) { this.info = info; }

		void INotifyAttack.PreparingAttack(Actor self, in Target target, Armament a, Barrel barrel) { }

		void INotifyAttack.Attacking(Actor self, in Target target, Armament a, Barrel barrel)
		{
			if (a == null || a.Info.Weapon == null)
				return;

			var weapon = a.Weapon;
			if (weapon.Range < info.MinRange)
				return;

			var heavy = false;
			foreach (var w in weapon.Warheads)
				if (w is DamageWarhead d && d.Damage >= info.HeavyDamage)
					heavy = true;

			var facing = self.TraitOrDefault<IFacing>()?.Facing ?? WAngle.Zero;
			var pos = self.CenterPosition + new WVec(0, -512, 0).Rotate(WRot.FromYaw(facing));
			Fx.Sprite(self.World, pos, info.Image, heavy ? info.HeavySequence : info.Sequence, info.Palette);
		}
	}
}

namespace OpenRA.Mods.TGMC.Traits
{
	using System;
	using System.Collections.Generic;
	using OpenRA.Graphics;
	using OpenRA.Primitives;

	[TraitLocation(SystemActors.World)]
	[Desc("A brief wash of light across the screen when a big blast goes off in view, brighter the closer to the middle of the screen it is. " +
		"Warheads add to it with the FlashScreen warhead.")]
	public class BlastFlashInfo : TraitInfo
	{
		[Desc("Colour of the flash (the alpha channel is ignored).")]
		public readonly Color Color = Color.FromArgb(255, 255, 235, 200);

		[Desc("The flash never gets brighter than this (0 to 255).")]
		public readonly int MaxAlpha = 150;

		public override object Create(ActorInitializer init) { return new BlastFlash(this); }
	}

	public class BlastFlash : ITick, IRenderOverlay, IWorldLoaded
	{
		readonly BlastFlashInfo info;
		readonly List<(int Left, int Total, float Strength)> flashes = [];
		WorldRenderer worldRenderer;

		public BlastFlash(BlastFlashInfo info) { this.info = info; }

		void IWorldLoaded.WorldLoaded(World w, WorldRenderer wr) { worldRenderer = wr; }

		// strength is 0 to 255 before the fade by distance.
		public void Add(WPos pos, int duration, int strength, WDist radius)
		{
			if (worldRenderer == null || duration <= 0)
				return;

			var distance = (pos - worldRenderer.Viewport.CenterPosition).HorizontalLength;
			var near = Math.Max(0f, 1f - distance / (float)Math.Max(1, radius.Length));
			if (near > 0)
				flashes.Add((duration, duration, strength * near));
		}

		void ITick.Tick(Actor self)
		{
			for (var i = flashes.Count - 1; i >= 0; i--)
			{
				var f = flashes[i];
				if (f.Left <= 1)
					flashes.RemoveAt(i);
				else
					flashes[i] = (f.Left - 1, f.Total, f.Strength);
			}
		}

		void IRenderOverlay.Render(WorldRenderer wr)
		{
			var alpha = 0f;
			foreach (var f in flashes)
			{
				var t = f.Left / (float)f.Total;
				alpha += f.Strength * t * t;
			}

			var a = (int)Math.Min(alpha, info.MaxAlpha);
			if (a <= 0)
				return;

			var tl = wr.Viewport.TopLeft;
			var br = wr.Viewport.BottomRight;
			Game.Renderer.WorldRgbaColorRenderer.FillRect(
				new System.Numerics.Vector3(tl.X, tl.Y, 0), new System.Numerics.Vector3(br.X, br.Y, 0),
				Color.FromArgb(a, info.Color), BlendMode.Additive);
		}
	}
}

namespace OpenRA.Mods.TGMC.Warheads
{
	using OpenRA.GameRules;
	using OpenRA.Mods.TGMC.Traits;
	using OpenRA.Traits;

	[Desc("Flashes the screen of anyone looking near the impact (see BlastFlash).")]
	public class FlashScreenWarhead : Warhead
	{
		[Desc("Ticks the flash lasts.")]
		public readonly int Duration = 8;

		[Desc("Brightness at the middle of the screen, 0 to 255.")]
		public readonly int Strength = 120;

		[Desc("The flash fades out this far from the middle of the screen.")]
		public readonly WDist Radius = new(24 * 1024);

		public override void DoImpact(in Target target, WarheadArgs args)
		{
			args.SourceActor.World.WorldActor.TraitOrDefault<BlastFlash>()?.Add(target.CenterPosition, Duration, Strength, Radius);
		}
	}
}
