#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Collections.Generic;
using OpenRA.Effects;
using OpenRA.GameRules;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Effects;
using OpenRA.Mods.Common.Graphics;
using OpenRA.Mods.Common.Orders;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Scripting;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("A CAS strike by the Condor: a jet roars across the map along a line through the target and drops bombs on it. " +
		"The jet is drawn from TGMC's own Condor art.")]
	public enum StrikePattern { Line, Single, Cluster }

	public class CondorStrikePowerInfo : SupportPowerInfo
	{
		[WeaponReference]
		[FieldLoader.Require]
		[Desc("Weapon of each bomb.")]
		public readonly string Weapon = null;

		[Desc("Name the Lua call ActivateCondorStrike uses to pick this ammo type.")]
		public readonly string Variant = "cas";

		[Desc("Line: bombs along the jet's track. Single: one missile at the target. Cluster: one missile, then a ring of blasts.")]
		public readonly StrikePattern Pattern = StrikePattern.Line;

		[Desc("Bombs dropped along the jet's track, centred on the target.")]
		public readonly int Bombs = 5;

		[WeaponReference]
		[Desc("Cluster only: weapon of each blast in the ring.")]
		public readonly string ClusterWeapon = null;

		[Desc("Cluster only: blasts in the ring, its radius, and ticks after the first blast.")]
		public readonly int ClusterCount = 8;
		public readonly WDist ClusterRadius = WDist.FromCells(4);
		public readonly int ClusterDelay = 75;

		[WeaponReference]
		[Desc("Weapon applied now and then to the ground where a strike landed, for napalm and lasers.")]
		public readonly string LingerWeapon = null;
		public readonly int LingerDuration = 0;
		public readonly int LingerInterval = 12;
		public readonly WDist LingerRadius = WDist.FromCells(3);
		[Desc("Spots hit per interval inside the radius.")]
		public readonly int LingerSpots = 3;

		[Desc("False: no aircraft. The blasts come straight down from orbit after FallDelay ticks (orbital bombardment).")]
		public readonly bool Jet = true;

		[Desc("Ticks the target area stays revealed after the strike (a flare). 0: just while the jet passes.")]
		public readonly int RevealDuration = 0;

		[Desc("Radius of the warning ring drawn on each spot before its blast, and of the targeting preview.")]
		public readonly WDist WarningRadius = WDist.FromCells(2);

		[Desc("Distance between bombs along the track.")]
		public readonly WDist Spacing = WDist.FromCells(2);

		[Desc("Ticks a bomb takes to fall after it is dropped.")]
		public readonly int FallDelay = 14;

		[Desc("How far before and after the target the jet's track runs.")]
		public readonly WDist TrackLength = WDist.FromCells(46);

		[Desc("Jet speed, in world distance per tick.")]
		public readonly WDist Speed = new(760);

		[Desc("How high the jet flies above the ground, and so how far its shadow falls from it.")]
		public readonly WDist Altitude = new(1600);

		public readonly string Image = "condor";
		public readonly string Sequence = "idle";
		public readonly string ShadowSequence = "shadow";
		public readonly string Palette = "effect";

		[Desc("Sound played as the jet starts its run, and as each bomb is dropped.")]
		public readonly string[] FlybySounds = [];

		[Desc("How far before the target the jet is when its flyby roar starts, and the sound played over the target as it passes overhead.")]
		public readonly WDist FlybyLead = new(12 * 1024);
		public readonly string[] PassSounds = [];
		public readonly string[] DropSounds = [];

		[Desc("Sounds played at the target spot as a bomb or missile comes down, IncomingLead ticks before it lands (at once if the fall is shorter).")]
		public readonly string[] IncomingSounds = [];
		public readonly int IncomingLead = 60;

		[Desc("How far around the target the player sees while the jet passes.")]
		public readonly WDist CameraRange = WDist.FromCells(8);

		public readonly Color CircleColor = Color.FromArgb(160, 255, 96, 32);

		public WeaponInfo WeaponInfo { get; private set; }
		public WeaponInfo ClusterWeaponInfo { get; private set; }
		public WeaponInfo LingerWeaponInfo { get; private set; }

		public override object Create(ActorInitializer init) { return new CondorStrikePower(init.Self, this); }

		public override void RulesetLoaded(Ruleset rules, ActorInfo ai)
		{
			WeaponInfo = rules.Weapons[Weapon.ToLowerInvariant()];
			if (ClusterWeapon != null)
				ClusterWeaponInfo = rules.Weapons[ClusterWeapon.ToLowerInvariant()];
			if (LingerWeapon != null)
				LingerWeaponInfo = rules.Weapons[LingerWeapon.ToLowerInvariant()];
			base.RulesetLoaded(rules, ai);
		}
	}

	public class CondorStrikePower : SupportPower
	{
		readonly CondorStrikePowerInfo info;

		public CondorStrikePower(Actor self, CondorStrikePowerInfo info)
			: base(self, info)
		{
			this.info = info;
		}

		public CondorStrikePowerInfo StrikeInfo => info;

		public override void SelectTarget(Actor self, string order, SupportPowerManager manager)
		{
			self.World.OrderGenerator = new CasTargetGenerator(order, manager, info, self);
		}

		public override void Activate(Actor self, Order order, SupportPowerManager manager)
		{
			base.Activate(self, order, manager);
			PlayLaunchSounds();
			Strike(self, order.Target.CenterPosition);
		}

		/// <summary>The unit vector (1024 long) the jet flies along for a strike at `target` called from `from`.</summary>
		public static WVec Heading(WPos from, WPos target)
		{
			var heading = new WVec(target.X - from.X, target.Y - from.Y, 0);
			if (heading.HorizontalLengthSquared == 0)
				return new WVec(1024, 0, 0);

			return heading * 1024 / heading.HorizontalLength;
		}

		/// <summary>Where each blast of the strike lands, so the targeting preview and the strike agree.</summary>
		public static IEnumerable<WPos> Spots(CondorStrikePowerInfo info, WPos target, WVec unit)
		{
			if (info.Pattern != StrikePattern.Line)
			{
				yield return target;
				yield break;
			}

			for (var i = 0; i < info.Bombs; i++)
				yield return target + unit * (int)((i - (info.Bombs - 1) / 2f) * info.Spacing.Length) / 1024;
		}

		public void Strike(Actor self, WPos target)
		{
			// The jet comes from the side the depot is on and flies through the target to the far side.
			var direction = Heading(self.CenterPosition, target);
			var track = direction * info.TrackLength.Length / 1024;
			var world = self.World;

			var owner = self.Owner;
			TgmcEventLog.Post(world, owner, "event-cas", target);
			world.WorldActor.TraitOrDefault<RadarPings>()?.Add(
				() => owner.IsAlliedWith(world.RenderPlayer), target, Color.FromArgb(255, 140, 40), 120);

			if (!info.Jet)
			{
				world.AddFrameEndTask(w => w.Add(new OrbitalBombardment(self, info, target)));
				world.AddFrameEndTask(w => w.Add(new RevealShroudEffect(target, info.CameraRange, Shroud.SourceType.Visibility, self.Owner,
					PlayerRelationship.Ally, 0, info.FallDelay + 40)));
				return;
			}

			var reveal = info.RevealDuration > 0
				? info.RevealDuration
				: (int)(2 * info.TrackLength.Length / Math.Max(1, info.Speed.Length)) + 40;

			world.AddFrameEndTask(w =>
			{
				w.Add(new CondorFlight(self, info, target - track, target + track, target));
				w.Add(new RevealShroudEffect(target, info.CameraRange, Shroud.SourceType.Visibility, self.Owner,
					PlayerRelationship.Ally, 0, reveal));
			});
		}
	}

	// While a strike is being chosen, show where its blasts will land, as the TGMC pilot's crosshair does.
	sealed class CasTargetGenerator : OrderGenerator
	{
		readonly string order;
		readonly SupportPowerManager manager;
		readonly CondorStrikePowerInfo info;
		readonly Actor depot;

		public CasTargetGenerator(string order, SupportPowerManager manager, CondorStrikePowerInfo info, Actor depot)
			: base(manager.Self.World)
		{
			this.order = order;
			this.manager = manager;
			this.info = info;
			this.depot = depot;
		}

		protected override MouseActionType ActionType => MouseActionType.SupportPower;

		protected override IEnumerable<Order> OrderInner(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			world.CancelInputMode();
			if (world.Map.Contains(cell))
				yield return new Order(order, manager.Self, Target.FromCell(world, cell), false) { SuppressVisualFeedback = true };
		}

		protected override void Tick(World world)
		{
			if (!manager.Powers.TryGetValue(order, out var p) || !p.Active || !p.Ready)
				world.CancelInputMode();
		}

		protected override IEnumerable<IRenderable> Render(WorldRenderer wr, World world) { yield break; }
		protected override IEnumerable<IRenderable> RenderAboveShroud(WorldRenderer wr, World world) { yield break; }

		protected override IEnumerable<IRenderable> RenderAnnotations(WorldRenderer wr, World world)
		{
			var cell = wr.Viewport.ViewToWorld(Viewport.LastMousePos);
			if (!world.Map.Contains(cell))
				yield break;

			var target = world.Map.CenterOfCell(cell);
			var unit = CondorStrikePower.Heading(depot.CenterPosition, target);
			var warn = info.CircleColor;
			foreach (var spot in CondorStrikePower.Spots(info, target, unit))
				yield return new CircleAnnotationRenderable(spot, info.WarningRadius, 1, warn);

			if (info.Pattern == StrikePattern.Cluster)
				yield return new CircleAnnotationRenderable(target, info.ClusterRadius + info.WarningRadius, 1, Color.FromArgb(110, 255, 200, 60));

			if (info.LingerDuration > 0)
				yield return new CircleAnnotationRenderable(target, info.LingerRadius, 1, Color.FromArgb(110, 255, 120, 20));
		}

		protected override string GetCursor(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			return world.Map.Contains(cell) ? info.Cursor : info.BlockedCursor;
		}
	}

	// The jet itself: one effect that flies the track, drops bombs as it crosses their spots, and applies the weapon after each
	// bomb's fall. Cluster missiles add a ring of blasts, and napalm and lasers leave burning ground.
	/// <summary>An orbital strike: no aircraft. Each spot's blast lands FallDelay ticks after the call, with the incoming whistle first.</summary>
	sealed class OrbitalBombardment : IEffect
	{
		readonly Actor source;
		readonly CondorStrikePowerInfo info;
		readonly WPos target;
		readonly WVec unit;
		int ticks;
		bool fired;

		public OrbitalBombardment(Actor source, CondorStrikePowerInfo info, WPos target)
		{
			this.source = source;
			this.info = info;
			this.target = target;
			unit = CondorStrikePower.Heading(source.CenterPosition, target);
		}

		void IEffect.Tick(World world)
		{
			ticks++;
			if (!fired && ticks == 1 && info.IncomingSounds.Length > 0)
				Fx.Sound(world, target, info.IncomingSounds);

			if (!fired && ticks >= info.FallDelay)
			{
				fired = true;
				foreach (var spot in CondorStrikePower.Spots(info, target, unit))
					Detonate(world, spot);

				world.AddFrameEndTask(w => w.Remove(this));
			}
		}

		void Detonate(World world, WPos spot)
		{
			var args = new WarheadArgs
			{
				Weapon = info.WeaponInfo,
				SourceActor = source,
				Source = spot,
				ImpactPosition = spot,
				WeaponTarget = Target.FromPos(spot),
				DamageModifiers = []
			};

			info.WeaponInfo.Impact(Target.FromPos(spot), args);
		}

		IEnumerable<IRenderable> IEffect.Render(WorldRenderer wr) { return SpriteRenderable.None; }
	}

	sealed class CondorFlight : IEffect
	{
		readonly Actor source;
		readonly CondorStrikePowerInfo info;
		readonly WVec step;
		readonly WVec unit;
		readonly WPos start;
		readonly WPos target;
		readonly int length;
		readonly Animation plane;
		readonly Animation shadow;
		readonly List<(int Tick, WPos Spot, WeaponInfo Weapon)> falling = [];
		readonly List<(WPos Spot, int Until)> burning = [];
		readonly List<(int Tick, WPos Spot)> whistles = [];

		WPos pos;
		int ticks;
		int dropped;
		bool done;
		bool roared;
		bool passed;

		public CondorFlight(Actor source, CondorStrikePowerInfo info, WPos start, WPos end, WPos target)
		{
			this.source = source;
			this.info = info;
			this.start = start;
			this.target = target;
			pos = start;

			var track = end - start;
			length = track.HorizontalLength;
			unit = track * 1024 / Math.Max(1, length);
			step = unit * info.Speed.Length / 1024;

			var world = source.World;
			// The sequences are facing-aware, so the nose points along the track whichever way that runs.
			var facing = unit.Yaw;
			plane = new Animation(world, info.Image, () => facing);
			plane.PlayRepeating(info.Sequence);
			shadow = new Animation(world, info.Image, () => facing);
			shadow.PlayRepeating(info.ShadowSequence);
		}

		public void Tick(World world)
		{
			if (done)
				return;

			ticks++;
			pos += step;
			var along = ((pos - start).X * unit.X + (pos - start).Y * unit.Y) / 1024;

			// The roar starts as the jet closes in and follows it; a second sound marks the moment it is overhead.
			if (!roared && along >= length / 2 - info.FlybyLead.Length)
			{
				roared = true;
				Fx.Sound(world, pos, info.FlybySounds);
			}

			if (!passed && along >= length / 2)
			{
				passed = true;
				Fx.Sound(world, target, info.PassSounds);
			}

			// Drop each bomb as the jet crosses its spot on the track, centred on the target.
			var centre = length / 2;
			var spots = info.Pattern == StrikePattern.Line ? info.Bombs : 1;
			while (dropped < spots && along >= centre + (info.Pattern == StrikePattern.Line ? (dropped - (info.Bombs - 1) / 2f) * info.Spacing.Length : 0))
			{
				var offset = info.Pattern == StrikePattern.Line ? (int)((dropped - (info.Bombs - 1) / 2f) * info.Spacing.Length) : 0;
				var spot = target + unit * offset / 1024;
				falling.Add((ticks + info.FallDelay, spot, info.WeaponInfo));
				Fx.Sound(world, spot, info.DropSounds);
				if (info.IncomingSounds.Length > 0)
					whistles.Add((ticks + System.Math.Max(0, info.FallDelay - info.IncomingLead), spot));
				dropped++;
			}

			for (var i = whistles.Count - 1; i >= 0; i--)
			{
				if (ticks < whistles[i].Tick)
					continue;

				Fx.Sound(world, whistles[i].Spot, info.IncomingSounds);
				whistles.RemoveAt(i);
			}

			for (var i = falling.Count - 1; i >= 0; i--)
			{
				if (ticks < falling[i].Tick)
					continue;

				var hit = falling[i];
				falling.RemoveAt(i);
				Detonate(world, hit.Spot, hit.Weapon);
				if (hit.Weapon == info.WeaponInfo)
					Landed(world, hit.Spot);
			}

			Burn(world);

			if (along > length && falling.Count == 0 && burning.Count == 0)
			{
				done = true;
				world.AddFrameEndTask(w => w.Remove(this));
			}
		}

		// After a primary blast: queue the cluster ring, start the ground fire, and light up the area for a flare.
		void Landed(World world, WPos spot)
		{
			if (info.Pattern == StrikePattern.Cluster && info.ClusterWeaponInfo != null)
			{
				for (var i = 0; i < info.ClusterCount; i++)
				{
					var angle = 1024 * i / info.ClusterCount;
					var ring = spot + new WVec(info.ClusterRadius.Length, 0, 0).Rotate(WRot.FromYaw(new WAngle(angle)));
					falling.Add((ticks + info.ClusterDelay, ring, info.ClusterWeaponInfo));
				}
			}

			if (info.LingerDuration > 0 && info.LingerWeaponInfo != null)
				burning.Add((spot, ticks + info.LingerDuration));
		}

		void Burn(World world)
		{
			if (burning.Count == 0 || ticks % Math.Max(1, info.LingerInterval) != 0)
			{
				burning.RemoveAll(b => ticks >= b.Until);
				return;
			}

			foreach (var (spot, until) in burning)
			{
				if (ticks >= until)
					continue;

				for (var i = 0; i < info.LingerSpots; i++)
				{
					var angle = new WAngle(world.SharedRandom.Next(1024));
					var distance = world.SharedRandom.Next(info.LingerRadius.Length + 1);
					Detonate(world, spot + new WVec(distance, 0, 0).Rotate(WRot.FromYaw(angle)), info.LingerWeaponInfo);
				}
			}

			burning.RemoveAll(b => ticks >= b.Until);
		}

		void Detonate(World world, WPos spot, WeaponInfo weapon)
		{
			var args = new WarheadArgs
			{
				Weapon = weapon,
				SourceActor = source,
				Source = spot,
				ImpactPosition = spot,
				WeaponTarget = Target.FromPos(spot),
				DamageModifiers = []
			};

			weapon.Impact(Target.FromPos(spot), args);
		}

		public IEnumerable<IRenderable> Render(WorldRenderer wr)
		{
			var palette = wr.Palette(info.Palette);
			var air = pos + new WVec(0, 0, info.Altitude.Length);

			foreach (var r in shadow.Render(pos, palette))
				yield return r;

			foreach (var r in plane.Render(air, WVec.Zero, 4000, palette))
				yield return r;

			// A pulsing ring on each spot waiting to be hit, so the player sees the danger zone.
			foreach (var (tick, spot, _) in falling)
			{
				var left = tick - ticks;
				var radius = new WDist(info.WarningRadius.Length * (left % 10 + 20) / 30);
				yield return new CircleAnnotationRenderable(spot, radius, 1, info.CircleColor);
			}
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using Eluant;
	using OpenRA.Mods.TGMC.Traits;

	[ScriptPropertyGroup("Support Powers")]
	public class CondorStrikeProperties : ScriptActorProperties, Requires<CondorStrikePowerInfo>
	{
		public CondorStrikeProperties(ScriptContext context, Actor self)
			: base(context, self) { }

		[Desc("Send the Condor in on a CAS strike at the cell. `variant` picks the ammo type (cas, gun, minirocket, widowmaker, napalm, " +
			"fatty, laser, flare, moab); with none, the plain bomb run.")]
		public void ActivateCondorStrike(CPos target, string variant = "cas")
		{
			foreach (var power in Self.TraitsImplementing<CondorStrikePower>())
			{
				if (power.StrikeInfo.Variant == variant)
				{
					power.Strike(Self, Self.World.Map.CenterOfCell(target));
					return;
				}
			}

			throw new LuaException($"The actor has no CAS ammo type '{variant}'.");
		}
	}
}
