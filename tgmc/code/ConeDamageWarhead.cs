#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose warheads this file extends.
#endregion

using System.Linq;
using OpenRA.GameRules;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Warheads
{
	[Desc("Damages every valid actor inside a cone that starts at the firer and points at the target. For flamers.")]
	public class ConeDamageWarhead : DamageWarhead
	{
		[Desc("How far the cone reaches from the firer.")]
		public readonly WDist ConeRange = WDist.FromCells(4);

		[Desc("Half of the cone's opening angle. 1024 is a full turn, so 64 is a 45 degree cone.")]
		public readonly WAngle HalfAngle = new(64);

		[Desc("Damage percentage at the far end of the cone. Falls off in a straight line from 100 at the firer.")]
		public readonly int FarEndPercent = 40;

		protected override void DoImpact(WPos pos, Actor firedBy, WarheadArgs args)
		{
			var origin = args.Source ?? firedBy.CenterPosition;
			var aim = args.ImpactPosition - origin;
			if (aim.LengthSquared == 0)
				return;

			var yaw = aim.Yaw;
			foreach (var victim in firedBy.World.FindActorsInCircle(origin, ConeRange))
			{
				if (victim == firedBy || !IsValidAgainst(victim, firedBy))
					continue;

				var offset = victim.CenterPosition - origin;
				if (offset.LengthSquared == 0)
					continue;

				var off = (offset.Yaw - yaw).Angle;
				if (off > 512)
					off = 1024 - off;

				if (off > HalfAngle.Angle)
					continue;

				var shape = victim.TraitsImplementing<HitShape>().FirstOrDefault(h => !h.IsTraitDisabled);
				if (shape == null)
					continue;

				var along = (int)(100L - (100L - FarEndPercent) * offset.Length / ConeRange.Length);
				InflictConeDamage(victim, firedBy, shape, args, along);
			}
		}

		void InflictConeDamage(Actor victim, Actor firedBy, HitShape shape, WarheadArgs args, int percent)
		{
			var damage = Util.ApplyPercentageModifiers(Damage, args.DamageModifiers);
			damage = damage * percent / 100;
			victim.InflictDamage(firedBy, new Damage(damage, DamageTypes));
		}
	}
}
