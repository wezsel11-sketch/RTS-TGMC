#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using System.Reflection;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits.Render;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Tints the actor's sprites toward its owner's colour, so two players on one side can be told apart. " +
		"The sprites are RGBA, which the player palette cannot recolour.")]
	public class WithPlayerTintInfo : TraitInfo
	{
		[Desc("How far a whole-sprite tint goes from white (0) to the full player colour (100). Cloth uses ClothSaturation and ClothBrightness.")]
		public readonly int Strength = 65;

		[Desc("How much of the player colour's saturation the cloth (armour, uniform, helmet) keeps, 0 to 100. Lower is greyer.")]
		public readonly int ClothSaturation = 60;

		[Desc("How bright the cloth colour is, 0 to 100 of the colour at full brightness. Lower is darker.")]
		public readonly int ClothBrightness = 75;

		public override object Create(ActorInitializer init) { return new WithPlayerTint(this); }
	}

	// A unit whose image has a "<image>-cloth" twin (mod/build_sprites.py, CLOTH layers) is drawn as it is, with the twin's
	// matching frame over it in the player colour. Any other unit has its whole sprite tinted.
	public class WithPlayerTint : IRenderModifier
	{
		// shortcut: SpriteRenderable keeps these private and has no "same again with another sprite";
		// drop the reflection if the engine ever grows one.
		const BindingFlags Private = BindingFlags.NonPublic | BindingFlags.Instance;
		static readonly FieldInfo SpriteField = typeof(SpriteRenderable).GetField("sprite", Private);
		static readonly FieldInfo ScaleField = typeof(SpriteRenderable).GetField("scale", Private);
		static readonly FieldInfo RotationField = typeof(SpriteRenderable).GetField("rotation", Private);

		readonly WithPlayerTintInfo info;
		Player owner;
		Vector3 tint;
		Dictionary<Sprite, Sprite> cloth;

		public WithPlayerTint(WithPlayerTintInfo info) { this.info = info; }

		static Dictionary<Sprite, Sprite> ClothOf(Actor self)
		{
			var map = new Dictionary<Sprite, Sprite>();
			var rs = self.TraitOrDefault<RenderSprites>();
			var sequences = self.World.Map.Sequences;
			var image = rs?.GetImage(self);
			if (image == null || !sequences.Images.Contains(image + "-cloth"))
				return map;

			foreach (var name in sequences.Sequences(image))
			{
				if (!sequences.HasSequence(image + "-cloth", name))
					continue;

				var a = sequences.GetSequence(image, name);
				var b = sequences.GetSequence(image + "-cloth", name);
				var facings = System.Math.Max(1, System.Math.Abs(a.Facings));
				for (var f = 0; f < facings; f++)
					for (var i = 0; i < a.Length; i++)
					{
						var angle = new WAngle(f * 1024 / facings);
						var sprite = a.GetSprite(i, angle);
						if (sprite != b.GetSprite(i, angle))
							map[sprite] = b.GetSprite(i, angle);
					}
			}

			return map;
		}

		IEnumerable<IRenderable> IRenderModifier.ModifyRender(Actor self, WorldRenderer wr, IEnumerable<IRenderable> r)
		{
			cloth ??= ClothOf(self);
			if (owner != self.Owner)
			{
				// The colour at full brightness: a dark player colour would otherwise black the unit out.
				owner = self.Owner;
				var c = owner.Color;
				var max = System.Math.Max(1, System.Math.Max((int)c.R, System.Math.Max((int)c.G, (int)c.B)));
				var full = new Vector3((float)c.R / max, (float)c.G / max, (float)c.B / max);
				if (cloth.Count > 0)
				{
					// Armour in the player colour, but toned down: part way to its own grey, then dimmed. Full strength glared.
					var grey = 0.299f * full.X + 0.587f * full.Y + 0.114f * full.Z;
					var sat = info.ClothSaturation / 100f;
					tint = (new Vector3(grey) * (1 - sat) + full * sat) * (info.ClothBrightness / 100f);
				}
				else
				{
					var s = info.Strength / 100f;
					tint = new Vector3(1 - s) + full * s;
				}
			}

			foreach (var a in r)
			{
				if (a is not SpriteRenderable sr || sr.IsDecoration)
					yield return a;
				else if (cloth.Count == 0)
					yield return sr.WithTint(sr.Tint * tint, sr.TintModifiers);
				else
				{
					yield return a;
					if (cloth.TryGetValue((Sprite)SpriteField.GetValue(sr), out var over))
						yield return new SpriteRenderable(over, sr.Pos, WVec.Zero, sr.ZOffset + 1, sr.Palette, (float)ScaleField.GetValue(sr),
							sr.Alpha, sr.Tint * tint, sr.TintModifiers, false, (WAngle)RotationField.GetValue(sr));
				}
			}
		}

		IEnumerable<Rectangle> IRenderModifier.ModifyScreenBounds(Actor self, WorldRenderer wr, IEnumerable<Rectangle> r) { return r; }
	}
}
