#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("The unit bleeds: a hit leaves a splash of blood on the floor, a heavy hit a bigger one, and a badly hurt unit drips as it walks. " +
		"The blood fades after about half a minute and is drawn under the units (see fx-blood in sequences).")]
	public class BleedsInfo : TraitInfo
	{
		public readonly string Image = "fx-blood";
		public readonly string Palette = "effect";

		[Desc("Percent chance that a hit leaves blood.")]
		public readonly int Chance = 70;

		[Desc("Hits weaker than this leave nothing.")]
		public readonly int MinDamage = 2;

		[Desc("Hits at least this strong leave a big splash.")]
		public readonly int BigDamage = 14;

		[Desc("Ticks between two splashes from one unit.")]
		public readonly int Cooldown = 10;

		[Desc("Below this share of its health a unit drips while it moves.")]
		public readonly int DripBelowPercent = 50;

		[Desc("Ticks between drips.")]
		public readonly int DripInterval = 35;

		public override object Create(ActorInitializer init) { return new Bleeds(init.Self, this); }
	}

	public class Bleeds : INotifyDamage, ITick
	{
		readonly BleedsInfo info;
		readonly Actor self;
		int cooldown;
		int drip;

		public Bleeds(Actor self, BleedsInfo info)
		{
			this.self = self;
			this.info = info;
		}

		void Splash(bool big)
		{
			var random = self.World.LocalRandom;
			var offset = new WVec(random.Next(-300, 300), random.Next(-200, 300), 0);
			var name = big ? "big" + random.Next(1, 7) : "small" + random.Next(1, 8);
			Fx.Sprite(self.World, self.CenterPosition + offset, info.Image, name, info.Palette);
		}

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			if (e.Damage.Value < info.MinDamage || cooldown > 0 || self.World.LocalRandom.Next(100) >= info.Chance)
				return;

			cooldown = info.Cooldown;
			Splash(e.Damage.Value >= info.BigDamage);
		}

		void ITick.Tick(Actor self)
		{
			if (cooldown > 0)
				cooldown--;

			if (self.IsDead || --drip > 0)
				return;

			drip = info.DripInterval;
			var health = self.TraitOrDefault<IHealth>();
			var mobile = self.TraitOrDefault<Mobile>();
			if (health != null && mobile != null && mobile.CurrentMovementTypes != MovementType.None
				&& health.HP * 100 < health.MaxHP * info.DripBelowPercent)
				Splash(false);
		}
	}
}
