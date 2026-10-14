#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using OpenRA.Effects;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Shows the damage this actor takes as a number that floats up from it, and healing in green. A lobby option can switch it off.")]
	public class DamageNumbersInfo : TraitInfo
	{
		public readonly string Font = "Bold";

		[Desc("Ticks a number stays up.")]
		public readonly int Lifetime = 28;

		[Desc("Height the number rises over its lifetime, in world units.")]
		public readonly int Rise = 640;

		public override object Create(ActorInitializer init) { return new DamageNumbers(this); }
	}

	public class DamageNumbers : INotifyDamage
	{
		readonly DamageNumbersInfo info;

		public DamageNumbers(DamageNumbersInfo info) { this.info = info; }

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			var amount = e.Damage.Value;
			if (amount == 0 || !Options.Enabled(self.World, Options.FloatingText, true))
				return;

			// Only what the viewer can see; the number is a picture, so it never touches the simulation.
			if (self.World.FogObscures(self))
				return;

			var viewer = self.World.RenderPlayer ?? self.World.LocalPlayer;
			var mine = viewer != null && self.Owner.IsAlliedWith(viewer);
			Color color;
			if (amount < 0)
				color = Color.FromArgb(110, 255, 120);
			else
				color = mine ? Color.FromArgb(255, 90, 80) : Color.FromArgb(255, 225, 120);

			var text = amount < 0 ? "+" + (-amount) : amount.ToString();
			var spread = self.World.LocalRandom.Next(-200, 201);
			var position = self.CenterPosition + new WVec(spread, 0, 400);
			self.World.AddFrameEndTask(w => w.Add(new FloatText(position, text, color, info)));
		}
	}

	sealed class FloatText : IEffect
	{
		readonly WPos start;
		readonly string text;
		readonly Color color;
		readonly DamageNumbersInfo info;
		readonly SpriteFont font;
		int age;

		public FloatText(WPos start, string text, Color color, DamageNumbersInfo info)
		{
			this.start = start;
			this.text = text;
			this.color = color;
			this.info = info;
			font = Game.Renderer.Fonts[info.Font];
		}

		public void Tick(World world)
		{
			if (++age >= info.Lifetime)
				world.AddFrameEndTask(w => w.Remove(this));
		}

		public IEnumerable<IRenderable> Render(WorldRenderer wr)
		{
			var pos = start + new WVec(0, 0, info.Rise * age / info.Lifetime);

			// Fade out over the last third of its life.
			var left = info.Lifetime - age;
			var alpha = left > info.Lifetime / 3 ? 255 : 255 * left * 3 / info.Lifetime;
			yield return new TextAnnotationRenderable(font, pos, 0, Color.FromArgb(alpha, color),
				Color.FromArgb(alpha, 20, 20, 20), Color.FromArgb(alpha, 20, 20, 20), text);
		}
	}
}
