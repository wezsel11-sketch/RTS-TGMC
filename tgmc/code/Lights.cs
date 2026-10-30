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

		[Desc("Ticks between two glows from one unit, so a burst does not pile up into a blinding flash.")]
		public readonly int Interval = 7;

		[Desc("Weapons that reach no further than this (claws, bites) give no glow.")]
		public readonly WDist MinRange = new(2048);

		public override object Create(ActorInitializer init) { return new MuzzleGlow(this); }
	}

	public class MuzzleGlow : INotifyAttack
	{
		readonly MuzzleGlowInfo info;
		int lastGlow = -1000;

		public MuzzleGlow(MuzzleGlowInfo info) { this.info = info; }

		void INotifyAttack.PreparingAttack(Actor self, in Target target, Armament a, Barrel barrel) { }

		void INotifyAttack.Attacking(Actor self, in Target target, Armament a, Barrel barrel)
		{
			if (a == null || a.Info.Weapon == null)
				return;

			var weapon = a.Weapon;
			if (weapon.Range < info.MinRange || self.World.WorldTick - lastGlow < info.Interval)
				return;

			lastGlow = self.World.WorldTick;

			var heavy = false;
			foreach (var w in weapon.Warheads)
				if (w is DamageWarhead d && d.Damage >= info.HeavyDamage)
					heavy = true;

			var facing = self.TraitOrDefault<IFacing>()?.Facing ?? WAngle.Zero;
			var pos = self.CenterPosition + new WVec(0, -512, 0).Rotate(WRot.FromYaw(facing));
			Fx.Sprite(self.World, pos, info.Image, heavy ? info.HeavySequence : info.Sequence, info.Palette);
			self.World.WorldActor.TraitOrDefault<NightLighting>()?.Add(pos, new WDist(heavy ? 3072 : 2048), heavy ? 1.1f : 0.7f,
				new System.Numerics.Vector3(1f, 0.85f, 0.55f), 4);
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
		public readonly int MaxAlpha = 70;

		public override object Create(ActorInitializer init) { return new BlastFlash(this); }
	}

	public class BlastFlash : ITick, IRenderOverlay, IWorldLoaded
	{
		readonly BlastFlashInfo info;
		readonly List<(int Left, int Total, float Strength)> flashes = [];
		WorldRenderer worldRenderer;

		public BlastFlash(BlastFlashInfo info) { this.info = info; }

		NightLighting night;

		void IWorldLoaded.WorldLoaded(World w, WorldRenderer wr)
		{
			worldRenderer = wr;
			night = w.WorldActor.TraitOrDefault<NightLighting>();
		}

		// strength is 0 to 255 before the fade by distance.
		public void Add(WPos pos, int duration, int strength, WDist radius)
		{
			if (worldRenderer == null || duration <= 0)
				return;

			// At night the blast also lights the ground around it, wherever the camera is.
			night?.Add(pos, new WDist(5120), Math.Min(1.5f, strength / 60f), new System.Numerics.Vector3(1f, 0.75f, 0.45f), duration);

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

namespace OpenRA.Mods.TGMC.Traits
{
	using System;
	using System.Collections.Generic;
	using System.Numerics;
	using OpenRA.Graphics;

	[TraitLocation(SystemActors.World | SystemActors.EditorWorld)]
	[Desc("Replaces TerrainLighting. By day the ground is at full light. With the lobby's Night option the ground drops to NightIntensity " +
		"under a cool moonlight tint, and NightLight actors and Flash calls (gunfire, blasts) light it up again around them.")]
	public class NightLightingInfo : TraitInfo
	{
		public readonly float NightIntensity = 0.38f;
		public readonly float NightRedTint = 0.8f;
		public readonly float NightGreenTint = 0.9f;
		public readonly float NightBlueTint = 1.15f;

		[Desc("No colour channel gets brighter than this, so overlapping lights do not burn the ground white.")]
		public readonly float MaxTint = 1.2f;

		public override object Create(ActorInitializer init) { return new NightLighting(init.World, this); }
	}

	public sealed class NightLighting : ITerrainLighting, ITick
	{
		public sealed class Light
		{
			public WPos Pos;
			public CPos Cell;
			public WDist Range;
			public float Intensity;
			public Vector3 Tint;
			public int Left, Total;
		}

		readonly NightLightingInfo info;
		readonly Map map;
		readonly List<Light> lights = [];
		readonly List<Light> flashes = [];
		readonly Vector3 ambient;

		public readonly bool IsNight;
		public event Action<MPos> CellChanged;

		public NightLighting(World world, NightLightingInfo info)
		{
			this.info = info;
			map = world.Map;
			IsNight = world.Type == WorldType.Regular && Options.Enabled(world, Options.Night, false);
			ambient = IsNight ? info.NightIntensity * new Vector3(info.NightRedTint, info.NightGreenTint, info.NightBlueTint) : Vector3.One;
		}

		// Lights only exist at night: by day every call is a no-op, so the day map renders exactly as before.
		public Light Add(WPos pos, WDist range, float intensity, Vector3 tint, int ticks = 0)
		{
			if (!IsNight)
				return null;

			var light = new Light { Pos = pos, Cell = map.CellContaining(pos), Range = range, Intensity = intensity, Tint = tint, Left = ticks, Total = ticks };
			(ticks > 0 ? flashes : lights).Add(light);
			Changed(light);
			return light;
		}

		public void Move(Light light, WPos pos)
		{
			if (light == null)
				return;

			light.Pos = pos;
			var cell = map.CellContaining(pos);
			if (cell == light.Cell)
				return;

			Changed(light);
			light.Cell = cell;
			Changed(light);
		}

		public void Remove(Light light)
		{
			if (light != null && lights.Remove(light))
				Changed(light);
		}

		void Changed(Light light)
		{
			if (CellChanged == null)
				return;

			foreach (var c in map.FindTilesInCircle(light.Cell, (light.Range.Length + 1023) / 1024))
				CellChanged(c.ToMPos(map));
		}

		void ITick.Tick(Actor self)
		{
			for (var i = flashes.Count - 1; i >= 0; i--)
			{
				var f = flashes[i];
				if (--f.Left <= 0)
					flashes.RemoveAt(i);

				Changed(f);
			}
		}

		static Vector3 Sum(List<Light> list, WPos pos, Vector3 tint, bool fade)
		{
			foreach (var l in list)
			{
				var range = l.Range.Length;
				var distance = (l.Pos - pos).HorizontalLength;
				if (distance >= range)
					continue;

				var falloff = (range - distance) * 1f / range * l.Intensity;
				if (fade)
					falloff *= l.Left * 1f / l.Total;

				tint += falloff * l.Tint;
			}

			return tint;
		}

		Vector3 ITerrainLighting.TintAt(WPos pos)
		{
			if (!IsNight)
				return ambient;

			var tint = Sum(flashes, pos, Sum(lights, pos, ambient, false), true);
			return Vector3.Min(tint, new Vector3(info.MaxTint));
		}
	}

	[Desc("A light the actor carries with it at night (a flashlight, headlights, base lamps, a fire's glow). Needs NightLighting on the world.")]
	public class NightLightInfo : ConditionalTraitInfo
	{
		public readonly WDist Range = new(4096);
		public readonly float Intensity = 0.6f;
		public readonly float RedTint = 1f;
		public readonly float GreenTint = 0.95f;
		public readonly float BlueTint = 0.85f;

		public override object Create(ActorInitializer init) { return new NightLight(this); }
	}

	public class NightLight : ConditionalTrait<NightLightInfo>, ITick, INotifyAddedToWorld, INotifyRemovedFromWorld
	{
		NightLighting lighting;
		NightLighting.Light light;

		public NightLight(NightLightInfo info)
			: base(info) { }

		protected override void Created(Actor self)
		{
			lighting = self.World.WorldActor.TraitOrDefault<NightLighting>();
			base.Created(self);
		}

		void Switch(Actor self, bool on)
		{
			if (lighting == null || !lighting.IsNight)
				return;

			lighting.Remove(light);
			light = on && self.IsInWorld && !IsTraitDisabled
				? lighting.Add(self.CenterPosition, Info.Range, Info.Intensity, new Vector3(Info.RedTint, Info.GreenTint, Info.BlueTint))
				: null;
		}

		void INotifyAddedToWorld.AddedToWorld(Actor self) { Switch(self, true); }
		void INotifyRemovedFromWorld.RemovedFromWorld(Actor self) { Switch(self, false); }
		protected override void TraitEnabled(Actor self) { Switch(self, true); }
		protected override void TraitDisabled(Actor self) { Switch(self, false); }

		void ITick.Tick(Actor self)
		{
			if (light != null)
				lighting.Move(light, self.CenterPosition);
		}
	}
}
