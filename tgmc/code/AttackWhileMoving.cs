#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Linq;
using OpenRA.Activities;
using OpenRA.Mods.Common.Activities;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Frontal attack that keeps firing at its target while the move child of the attack activity is still running.")]
	public class AttackWhileMovingInfo : AttackFrontalInfo
	{
		[Desc("False for heavy weapons (sniper, machine gun): they stop to shoot, like a plain frontal attack.")]
		public readonly bool FireWhileMoving = true;

		[Desc("How far off its heading (1024 is a full turn) a target may be for a unit that is walking along to shoot at it.")]
		public readonly WAngle WalkFacingTolerance = new(200);

		[Desc("The unit holds fire when a wall or a closed door stands between it and the target (it can be seen by a friend, but not hit).")]
		public readonly bool NeedsLineOfFire = true;

		[Desc("Ticks between looks for an enemy while walking, so a unit on the move also shoots at what it passes.")]
		public readonly int ScanInterval = 8;

		public override object Create(ActorInitializer init) { return new AttackWhileMoving(init.Self, this); }
	}

	public class AttackWhileMoving : AttackFrontal
	{
		public new readonly AttackWhileMovingInfo Info;
		AutoTarget autoTarget;
		int scanCountdown;

		public AttackWhileMoving(Actor self, AttackWhileMovingInfo info)
			: base(self, info)
		{
			Info = info;
		}

		// Holds fire at a target behind a wall: sight is shared across the army, so a friend can see what this unit cannot hit.
		protected override bool CanAttack(Actor self, in Target target)
		{
			if (!base.CanAttack(self, target))
				return false;

			if (!Info.NeedsLineOfFire || target.Type == TargetType.Invalid)
				return true;

			var cell = target.Type == TargetType.Actor ? target.Actor.Location : self.World.Map.CellContaining(target.CenterPosition);
			return Traits.TgmcSight.ClearLine(self.World, self.Location, cell);
		}

		// Walking along on a move or attack-move order: shoot at the nearest enemy in range without stopping.
		protected override void Tick(Actor self)
		{
			base.Tick(self);

			autoTarget ??= self.TraitOrDefault<AutoTarget>();
			if (!Info.FireWhileMoving || IsTraitDisabled || IsTraitPaused || autoTarget == null || --scanCountdown > 0)
				return;

			scanCountdown = Info.ScanInterval;
			if (self.CurrentActivity == null || self.CurrentActivity is FireOnMove || self.CurrentActivity is Attack)
				return;

			var mobile = self.TraitOrDefault<Mobile>();
			if (mobile == null || mobile.CurrentMovementTypes == MovementType.None && !(self.CurrentActivity is Move))
				return;

			var target = autoTarget.ScanForTarget(self, false, true, true);
			if (!target.IsValidFor(self))
				return;

			var facing = self.Trait<IFacing>();
			var armaments = ChooseArmamentsForTarget(target, false)
				.Where(a => !a.IsTraitPaused && target.IsInRange(self.CenterPosition, a.MaxRange()))
				.ToList();

			if (armaments.Count == 0 || !TargetInFiringArc(self, target, Info.WalkFacingTolerance))
				return;

			foreach (var a in armaments)
				a.CheckFire(self, facing, target);
		}

		public override Activity GetAttackActivity(
			Actor self, AttackSource source, in Target newTarget, bool allowMove, bool forceAttack, Color? targetLineColor = null)
		{
			if (!Info.FireWhileMoving)
				return base.GetAttackActivity(self, source, newTarget, allowMove, forceAttack, targetLineColor);

			return new FireOnMove(self, newTarget, allowMove, forceAttack, targetLineColor);
		}
	}

	// The engine's Attack activity runs its move child first and fires only once the child has finished. This subclass
	// fires from the same target while that child runs, then hands over to the base activity for everything else.
	public class FireOnMove : Attack
	{
		public FireOnMove(Actor self, in Target target, bool allowMovement, bool forceAttack, Color? targetLineColor = null)
			: base(self, target, allowMovement, forceAttack, targetLineColor) { }

		public override bool Tick(Actor self)
		{
			if (!IsCanceling && ChildActivity != null)
			{
				// Still closing in on the target: a Runner or Hunter may leap at it now.
				self.TraitOrDefault<Pounce>()?.TryPounce(self, target);
				FireWhileMoving(self);
			}

			return base.Tick(self);
		}

		void FireWhileMoving(Actor self)
		{
			var facing = self.Trait<IFacing>();
			if (!target.IsValidFor(self))
				return;

			foreach (var attack in self.TraitsImplementing<AttackWhileMoving>())
			{
				if (attack.IsTraitDisabled || attack.IsTraitPaused)
					continue;

				var armaments = attack.ChooseArmamentsForTarget(target, false)
					.Where(a => !a.IsTraitPaused && target.IsInRange(self.CenterPosition, a.MaxRange()))
					.ToList();

				if (armaments.Count == 0 || !attack.TargetInFiringArc(self, target, attack.Info.FacingTolerance))
					continue;

				foreach (var a in armaments)
					a.CheckFire(self, facing, target);
			}
		}
	}
}
