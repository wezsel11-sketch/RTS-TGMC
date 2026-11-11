#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using OpenRA.Graphics;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Tints the actor's sprites toward its owner's colour, so two players on one side can be told apart. " +
		"The sprites are RGBA, which the player palette cannot recolour.")]
	public class WithPlayerTintInfo : TraitInfo
	{
		[Desc("How far the tint goes from white (0) to the full player colour (100).")]
		public readonly int Strength = 65;

		public override object Create(ActorInitializer init) { return new WithPlayerTint(this); }
	}

	// shortcut: the whole sprite is tinted, skin and gun too; split a cloth mask out in build_sprites.py if that shows.
	public class WithPlayerTint : IRenderModifier
	{
		readonly WithPlayerTintInfo info;
		Player owner;
		Vector3 tint;

		public WithPlayerTint(WithPlayerTintInfo info) { this.info = info; }

		IEnumerable<IRenderable> IRenderModifier.ModifyRender(Actor self, WorldRenderer wr, IEnumerable<IRenderable> r)
		{
			if (owner != self.Owner)
			{
				// The colour at full brightness: a dark player colour would otherwise black the unit out.
				owner = self.Owner;
				var c = owner.Color;
				var max = System.Math.Max(1, System.Math.Max((int)c.R, System.Math.Max((int)c.G, (int)c.B)));
				var s = info.Strength / 100f;
				tint = new Vector3(1 - s + s * c.R / max, 1 - s + s * c.G / max, 1 - s + s * c.B / max);
			}

			return r.Select(a => a is SpriteRenderable sr && !sr.IsDecoration ? sr.WithTint(sr.Tint * tint, sr.TintModifiers) : a);
		}

		IEnumerable<Rectangle> IRenderModifier.ModifyScreenBounds(Actor self, WorldRenderer wr, IEnumerable<Rectangle> r) { return r; }
	}
}
