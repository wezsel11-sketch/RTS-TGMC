#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Like DamageMultiplier, but only for some kinds of damage: armour that acid walks through, a gas mask that only helps against gas.")]
	public class TypedDamageMultiplierInfo : ConditionalTraitInfo
	{
		[FieldLoader.Require]
		[Desc("Percentage modifier to apply.")]
		public readonly int Modifier = 100;

		[Desc("Damage types the modifier applies to. Empty means all of them.")]
		public readonly BitSet<DamageType> DamageTypes = default;

		[Desc("Damage types the modifier does not apply to.")]
		public readonly BitSet<DamageType> IgnoredDamageTypes = default;

		public override object Create(ActorInitializer init) { return new TypedDamageMultiplier(this); }
	}

	public class TypedDamageMultiplier : ConditionalTrait<TypedDamageMultiplierInfo>, IDamageModifier
	{
		public TypedDamageMultiplier(TypedDamageMultiplierInfo info)
			: base(info) { }

		int IDamageModifier.GetDamageModifier(Actor attacker, Damage damage)
		{
			if (IsTraitDisabled || damage == null)
				return 100;

			if (!Info.DamageTypes.IsEmpty && !damage.DamageTypes.Overlaps(Info.DamageTypes))
				return 100;

			return damage.DamageTypes.Overlaps(Info.IgnoredDamageTypes) ? 100 : Info.Modifier;
		}
	}
}
