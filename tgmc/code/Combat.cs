#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Every shot this actor fires does a random share of its weapon's damage, so no two hits are the same.")]
	public class DamageVariationInfo : ConditionalTraitInfo
	{
		[Desc("Lowest percentage of the weapon's damage a shot can do.")]
		public readonly int MinPercent = 85;

		[Desc("Highest percentage of the weapon's damage a shot can do.")]
		public readonly int MaxPercent = 115;

		public override object Create(ActorInitializer init) { return new DamageVariation(init.Self, this); }
	}

	public class DamageVariation : ConditionalTrait<DamageVariationInfo>, IFirepowerModifier
	{
		readonly Actor self;

		public DamageVariation(Actor self, DamageVariationInfo info)
			: base(info)
		{
			this.self = self;
		}

		// Armament asks for the modifiers as it creates each shot, inside the simulation, so SharedRandom stays in step.
		int IFirepowerModifier.GetFirepowerModifier()
		{
			if (IsTraitDisabled)
				return 100;

			return self.World.SharedRandom.Next(Info.MinPercent, Info.MaxPercent + 1);
		}
	}

	[Desc("A leap at an enemy being chased: the actor grants itself a condition (for a speed burst) for a moment, and a " +
		"second condition (to enable a stunning strike) a little longer, then has to wait out the cooldown. After the xeno " +
		"Runner and Hunter pounce of TGMC.")]
	public class PounceInfo : ConditionalTraitInfo
	{
		[Desc("Farthest the target may be for the pounce to start.")]
		public readonly WDist Range = WDist.FromCells(5);

		[Desc("Closest the target may be; nearer than this the actor just attacks.")]
		public readonly WDist MinRange = WDist.FromCells(2);

		[Desc("Ticks the leap condition lasts.")]
		public readonly int Duration = 16;

		[Desc("Ticks the strike condition lasts, counted from the start of the leap.")]
		public readonly int StrikeWindow = 40;

		[Desc("Ticks before the actor can pounce again.")]
		public readonly int Cooldown = 300;

		[GrantedConditionReference]
		public readonly string Condition = "pouncing";

		[GrantedConditionReference]
		public readonly string StrikeCondition = "pounce-strike";

		[Desc("Sounds played as the actor leaps.")]
		public readonly string[] Sounds = [];

		public override object Create(ActorInitializer init) { return new Pounce(this); }
	}

	public class Pounce : ConditionalTrait<PounceInfo>, ITick, ISelectionBar
	{
		int cooldown;
		int leapLeft;
		int strikeLeft;
		int leapToken = Actor.InvalidConditionToken;
		int strikeToken = Actor.InvalidConditionToken;

		public Pounce(PounceInfo info)
			: base(info) { }

		public int CooldownRemaining => cooldown;

		// A blue bar that fills as the ability recharges, and goes away when it is ready.
		float ISelectionBar.GetValue()
		{
			return cooldown > 0 ? 1f - cooldown / (float)System.Math.Max(1, Info.Cooldown) : 0f;
		}

		Color ISelectionBar.GetColor() { return Color.FromArgb(90, 160, 255); }
		bool ISelectionBar.DisplayWhenEmpty => false;

		public void TryPounce(Actor self, in Target target)
		{
			if (IsTraitDisabled || cooldown > 0 || target.Type != TargetType.Actor)
				return;

			if (self.Owner.RelationshipWith(target.Actor.Owner) != PlayerRelationship.Enemy)
				return;

			var distance = (target.CenterPosition - self.CenterPosition).Length;
			if (distance > Info.Range.Length || distance < Info.MinRange.Length)
				return;

			cooldown = Info.Cooldown;
			leapLeft = Info.Duration;
			strikeLeft = Info.StrikeWindow;
			leapToken = self.GrantCondition(Info.Condition);
			strikeToken = self.GrantCondition(Info.StrikeCondition);
			Fx.Sound(self.World, self.CenterPosition, Info.Sounds);
		}

		void ITick.Tick(Actor self)
		{
			if (cooldown > 0)
				cooldown--;

			if (leapToken != Actor.InvalidConditionToken && --leapLeft <= 0)
				leapToken = self.RevokeCondition(leapToken);

			if (strikeToken != Actor.InvalidConditionToken && --strikeLeft <= 0)
				strikeToken = self.RevokeCondition(strikeToken);
		}
	}
}
