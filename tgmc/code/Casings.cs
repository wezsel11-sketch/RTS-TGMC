#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using OpenRA.Effects;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Flings a spent cartridge case to the side each time one of the listed weapons fires. Only a picture: it never touches the simulation.")]
	public class EjectsCasingsInfo : ConditionalTraitInfo
	{
		[Desc("Weapons that leave a casing.")]
		public readonly HashSet<string> Weapons = [];

		public readonly string Image = "fx-casing";
		public readonly string Sequence = "idle";
		public readonly string Palette = "effect";

		[Desc("Ticks a casing lies on the ground before it fades, and ticks the fade takes.")]
		public readonly int Linger = 75;
		public readonly int Fade = 25;

		public override object Create(ActorInitializer init) { return new EjectsCasings(this); }
	}

	public class EjectsCasings : ConditionalTrait<EjectsCasingsInfo>, INotifyAttack
	{
		public EjectsCasings(EjectsCasingsInfo info)
			: base(info) { }

		void INotifyAttack.PreparingAttack(Actor self, in Target target, Armament a, Barrel barrel) { }

		void INotifyAttack.Attacking(Actor self, in Target target, Armament a, Barrel barrel)
		{
			if (IsTraitDisabled || !Info.Weapons.Contains(a.Info.Weapon))
				return;

			var world = self.World;
			if (world.FogObscures(self))
				return;

			var facing = self.TraitOrDefault<IFacing>()?.Facing ?? WAngle.Zero;
			var rotation = WRot.FromYaw(facing);

			// Out of the right-hand side and a little back, up and away.
			var origin = self.CenterPosition + new WVec(0, 0, 420) + new WVec(-60, 150, 0).Rotate(rotation);
			var kick = new WVec(-14 + world.LocalRandom.Next(-8, 9), 34 + world.LocalRandom.Next(-8, 9), 0).Rotate(rotation);
			var up = 38 + world.LocalRandom.Next(-8, 9);
			var spin = 20 + world.LocalRandom.Next(0, 30);
			world.AddFrameEndTask(w => w.Add(new Casing(w, origin, kick, up, spin, Info)));
		}
	}

	// One casing: arcs out, lands, lies still and then fades.
	sealed class Casing : IEffect
	{
		const int Gravity = 5;

		readonly Animation anim;
		readonly EjectsCasingsInfo info;
		readonly WVec kick;
		readonly int spin;
		WPos pos;
		int up;
		int age;
		int landedAt = -1;
		WAngle turn;

		public Casing(World world, WPos pos, WVec kick, int up, int spin, EjectsCasingsInfo info)
		{
			this.pos = pos;
			this.kick = kick;
			this.up = up;
			this.spin = spin;
			this.info = info;
			anim = new Animation(world, info.Image, () => turn);
			anim.PlayRepeating(info.Sequence);
		}

		public void Tick(World world)
		{
			age++;
			if (landedAt < 0)
			{
				pos += kick + new WVec(0, 0, up);
				up -= Gravity;
				turn += new WAngle(spin);
				if (pos.Z <= 0)
				{
					pos = new WPos(pos.X, pos.Y, 0);
					landedAt = age;
				}
			}
			else if (age - landedAt > info.Linger + info.Fade)
				world.AddFrameEndTask(w => w.Remove(this));
		}

		public IEnumerable<IRenderable> Render(WorldRenderer wr)
		{
			var alpha = 1f;
			if (landedAt >= 0)
			{
				var faded = age - landedAt - info.Linger;
				if (faded > 0)
					alpha = System.Math.Max(0f, 1f - faded / (float)System.Math.Max(1, info.Fade));
			}

			foreach (var r in anim.Render(pos, wr.Palette(info.Palette)))
				yield return alpha < 1f && r is IModifyableRenderable m ? m.WithAlpha(alpha) : r;
		}
	}
}
