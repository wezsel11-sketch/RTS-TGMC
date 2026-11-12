#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Primitives;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("A puff on the ground under alternating feet while the unit walks (the mech's dust, TGMC's mech_footstep particles).")]
	public class StepEffectInfo : ConditionalTraitInfo
	{
		public readonly string Image = "fx-dirt-puff";
		public readonly string Sequence = "idle";
		public readonly string Palette = "effect";

		[Desc("Ticks between two steps while walking.")]
		public readonly int Interval = 8;

		[Desc("How far to the side of the unit's centre each foot falls.")]
		public readonly WDist FootSpread = new(320);

		public readonly string[] Sounds = [];

		public override object Create(ActorInitializer init) { return new StepEffect(this); }
	}

	public class StepEffect : ConditionalTrait<StepEffectInfo>, ITick
	{
		IMove move;
		IFacing facing;
		int ticks;
		bool left;

		public StepEffect(StepEffectInfo info)
			: base(info) { }

		protected override void Created(Actor self)
		{
			move = self.TraitOrDefault<IMove>();
			facing = self.TraitOrDefault<IFacing>();
			base.Created(self);
		}

		void ITick.Tick(Actor self)
		{
			if (IsTraitDisabled || move == null || move.CurrentMovementTypes == MovementType.None || --ticks > 0)
				return;

			ticks = Info.Interval;
			left = !left;
			var side = new WVec(left ? -Info.FootSpread.Length : Info.FootSpread.Length, 0, 0).Rotate(WRot.FromYaw(facing?.Facing ?? WAngle.Zero));
			var pos = self.CenterPosition + side;
			Fx.Sprite(self.World, new WPos(pos.X, pos.Y, 0), Info.Image, Info.Sequence, Info.Palette);
			Fx.Sound(self.World, pos, Info.Sounds);
		}
	}

	[Desc("A puff of smoke at the gun each time the unit fires (TGMC's firing_smoke particles).")]
	public class FireSmokeInfo : ConditionalTraitInfo
	{
		public readonly string Image = "fx-smoke-puff";
		public readonly string Sequence = "idle";
		public readonly string Palette = "effect";

		[Desc("Where the smoke appears, in front of the unit's centre and up.")]
		public readonly WVec Offset = new(0, -512, 384);

		[Desc("Only these armaments make smoke. Empty for all.")]
		public readonly string[] Armaments = [];

		public override object Create(ActorInitializer init) { return new FireSmoke(this); }
	}

	public class FireSmoke : ConditionalTrait<FireSmokeInfo>, INotifyAttack
	{
		public FireSmoke(FireSmokeInfo info)
			: base(info) { }

		void INotifyAttack.Attacking(Actor self, in Target target, Armament a, Barrel barrel)
		{
			if (IsTraitDisabled || (Info.Armaments.Length > 0 && !Info.Armaments.Contains(a.Info.Name)))
				return;

			var yaw = (target.CenterPosition - self.CenterPosition).Yaw;
			Fx.Sprite(self.World, self.CenterPosition + Info.Offset.Rotate(WRot.FromYaw(yaw)), Info.Image, Info.Sequence, Info.Palette);
		}

		void INotifyAttack.PreparingAttack(Actor self, in Target target, Armament a, Barrel barrel) { }
	}

	[Desc("The body darts toward a close target on each attack and settles back (TGMC's attack animation is this lunge; it has no attack frames).")]
	public class AttackLungeInfo : TraitInfo
	{
		[Desc("How far the body moves at the peak.")]
		public readonly WDist Distance = new(360);

		[Desc("Ticks from the strike until the body is back.")]
		public readonly int Duration = 7;

		[Desc("Targets further than this get no lunge (spit and other ranged attacks).")]
		public readonly WDist MaxRange = new(2048);

		public override object Create(ActorInitializer init) { return new AttackLunge(this); }
	}

	public class AttackLunge : INotifyAttack, ITick, IRenderModifier
	{
		readonly AttackLungeInfo info;
		WVec reach;
		int left;

		public AttackLunge(AttackLungeInfo info) { this.info = info; }

		void INotifyAttack.Attacking(Actor self, in Target target, Armament a, Barrel barrel)
		{
			var to = target.CenterPosition - self.CenterPosition;
			if (to.HorizontalLength == 0 || to.HorizontalLength > info.MaxRange.Length)
				return;

			reach = new WVec(to.X, to.Y, 0) * info.Distance.Length / to.HorizontalLength;
			left = info.Duration;
		}

		void INotifyAttack.PreparingAttack(Actor self, in Target target, Armament a, Barrel barrel) { }

		void ITick.Tick(Actor self)
		{
			if (left > 0)
				left--;
		}

		IEnumerable<IRenderable> IRenderModifier.ModifyRender(Actor self, WorldRenderer wr, IEnumerable<IRenderable> r)
		{
			if (left == 0)
				return r;

			// Out in the first two ticks, back over the rest.
			var passed = info.Duration - left;
			var shift = passed < 2 ? reach * (passed + 1) / 2 : reach * left / (info.Duration - 1);
			return r.Select(x => x.OffsetBy(shift));
		}

		IEnumerable<Rectangle> IRenderModifier.ModifyScreenBounds(Actor self, WorldRenderer wr, IEnumerable<Rectangle> bounds)
		{
			return bounds;
		}
	}

	[Desc("Sparks fly off the unit when it is hit (armour: the mech). Healing makes none.")]
	public class HitSparksInfo : ConditionalTraitInfo
	{
		public readonly string Image = "fx-spark";
		public readonly string Sequence = "idle";
		public readonly string Palette = "effect";

		[Desc("Hits smaller than this make no sparks.")]
		public readonly int MinDamage = 5;

		[Desc("How far from the centre the sparks may show.")]
		public readonly WDist Scatter = new(384);

		public readonly string[] Sounds = [];

		public override object Create(ActorInitializer init) { return new HitSparks(this); }
	}

	public class HitSparks : ConditionalTrait<HitSparksInfo>, INotifyDamage
	{
		public HitSparks(HitSparksInfo info)
			: base(info) { }

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			if (IsTraitDisabled || e.Damage.Value < Info.MinDamage || self.IsDead)
				return;

			// Only a picture: the local random keeps the game's shared one untouched.
			var r = self.World.LocalRandom;
			var s = Info.Scatter.Length;
			var pos = self.CenterPosition + new WVec(r.Next(-s, s + 1), r.Next(-s, s + 1), r.Next(128, s + 256));
			Fx.Sprite(self.World, pos, Info.Image, Info.Sequence, Info.Palette);
			Fx.Sound(self.World, pos, Info.Sounds);
		}
	}
}
