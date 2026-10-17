#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using OpenRA.Activities;
using OpenRA.GameRules;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Warheads
{
	[Desc("Throws the victim away from the firer: it flies in an arc over several cells and lands, taking damage when it lands and more if " +
		"something blocks it on the way (a wall, a building, another unit). Only units that walk can be thrown.")]
	public class KnockbackWarhead : Warhead
	{
		[Desc("How far the victim is thrown.")]
		public readonly WDist Distance = new(3 * 1024);

		[Desc("Ticks the flight takes.")]
		public readonly int Duration = 14;

		[Desc("Height of the arc at its highest.")]
		public readonly WDist Height = new(1024);

		[Desc("Damage taken on landing.")]
		public readonly int LandDamage = 0;

		[Desc("Extra damage if the throw is cut short by an obstacle.")]
		public readonly int BlockedDamage = 0;

		public readonly BitSet<DamageType> DamageTypes = default;

		public override void DoImpact(in Target target, WarheadArgs args)
		{
			var firedBy = args.SourceActor;
			var victim = target.Type == TargetType.Actor ? target.Actor : null;
			if (firedBy == null || victim == null || victim.IsDead || !victim.IsInWorld || !IsValidAgainst(victim, firedBy))
				return;

			Throw(victim, firedBy, args.Source ?? firedBy.CenterPosition, Distance, Duration, Height, LandDamage, BlockedDamage, DamageTypes);
		}

		/// <summary>Throws a unit away from `from`: it flies an arc over `distance` and lands, or stops short at an obstacle.</summary>
		public static void Throw(Actor victim, Actor firedBy, WPos from, WDist distance, int duration, WDist height, int landDamage, int blockedDamage, BitSet<DamageType> damageTypes)
		{
			var mobile = victim.TraitOrDefault<Mobile>();
			if (mobile == null || victim.CurrentActivity is Thrown)
				return;

			var world = victim.World;
			var away = victim.CenterPosition - from;
			if (away.HorizontalLengthSquared == 0)
				away = new WVec(1024, 0, 0);

			var step = new WVec(away.X, away.Y, 0) * 1024 / away.HorizontalLength;
			var cells = Math.Max(1, distance.Length / 1024);
			var landing = victim.Location;
			var blocked = false;
			for (var i = 1; i <= cells; i++)
			{
				var cell = world.Map.CellContaining(victim.CenterPosition + step * i);
				if (!world.Map.Contains(cell) || !mobile.CanEnterCell(cell, victim))
				{
					blocked = true;
					break;
				}

				landing = cell;
			}

			if (landing == victim.Location)
			{
				if (blocked && blockedDamage > 0)
					victim.InflictDamage(firedBy, new Damage(blockedDamage, damageTypes));

				return;
			}

			victim.CancelActivity();
			victim.QueueActivity(new Thrown(victim, mobile, landing, duration, height.Length,
				landDamage + (blocked ? blockedDamage : 0), firedBy, damageTypes));
		}
	}

	sealed class Thrown : Activity
	{
		readonly Mobile mobile;
		readonly WPos start;
		readonly WPos end;
		readonly CPos landing;
		readonly int duration;
		readonly int height;
		readonly int damage;
		readonly Actor thrower;
		readonly BitSet<DamageType> damageTypes;
		int elapsed;

		public Thrown(Actor self, Mobile mobile, CPos landing, int duration, int height, int damage, Actor thrower, BitSet<DamageType> damageTypes)
		{
			this.mobile = mobile;
			this.landing = landing;
			this.duration = Math.Max(1, duration);
			this.height = height;
			this.damage = damage;
			this.thrower = thrower;
			this.damageTypes = damageTypes;
			start = self.CenterPosition;
			end = self.World.Map.CenterOfCell(landing);
			IsInterruptible = false;
		}

		public override bool Tick(Actor self)
		{
			elapsed++;
			var f = Math.Min(1f, elapsed / (float)duration);
			var progress = Math.Min(elapsed, duration);
			var flat = start + (end - start) * progress / duration;
			var lift = (int)(4f * height * f * (1f - f));
			mobile.SetCenterPosition(self, new WPos(flat.X, flat.Y, start.Z + lift));

			if (elapsed < duration)
				return false;

			mobile.SetPosition(self, landing);
			if (damage > 0 && !self.IsDead)
				self.InflictDamage(thrower, new Damage(damage, damageTypes));

			return true;
		}
	}
}
