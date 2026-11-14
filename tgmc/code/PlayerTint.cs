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
	[Desc("Colours a unit for its owner. A unit with a \"<image>-cloth\" twin (armour, uniform, a mech's paint; mod/build_sprites.py) has it drawn " +
		"over the unit through the owner's TGMC armour palette (TgmcArmorPalette), and a unit with \"<image>-camo-<style>\" twins has the map's " +
		"camo (TgmcCamo) drawn over its standard armour. Any other unit (xenos, vehicles) has its whole sprite tinted toward the owner's colour.")]
	public class WithPlayerTintInfo : TraitInfo
	{
		[Desc("How far a whole-sprite tint goes from white (0) to the full player colour (100).")]
		public readonly int Strength = 65;

		[Desc("The palettes TgmcArmorPalette adds, one per player: this name and the player's internal name.")]
		public readonly string ArmorPalette = "tgmcarmor";

		public override object Create(ActorInitializer init) { return new WithPlayerTint(this); }
	}

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
		Dictionary<Sprite, Sprite> camo;

		public WithPlayerTint(WithPlayerTintInfo info) { this.info = info; }

		// The sprite of a twin image for each sprite of the unit's own image, frame by frame and facing by facing.
		static Dictionary<Sprite, Sprite> TwinOf(Actor self, string suffix)
		{
			var map = new Dictionary<Sprite, Sprite>();
			var rs = self.TraitOrDefault<RenderSprites>();
			var sequences = self.World.Map.Sequences;
			var image = rs?.GetImage(self);
			if (image == null || suffix == null || !sequences.Images.Contains(image + suffix))
				return map;

			foreach (var name in sequences.Sequences(image))
			{
				if (!sequences.HasSequence(image + suffix, name))
					continue;

				var a = sequences.GetSequence(image, name);
				var b = sequences.GetSequence(image + suffix, name);
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

		static SpriteRenderable Over(SpriteRenderable sr, Sprite sprite, int z, PaletteReference palette)
		{
			return new SpriteRenderable(sprite, sr.Pos, WVec.Zero, sr.ZOffset + z, palette, (float)ScaleField.GetValue(sr),
				sr.Alpha, sr.Tint, sr.TintModifiers, false, (WAngle)RotationField.GetValue(sr));
		}

		IEnumerable<IRenderable> IRenderModifier.ModifyRender(Actor self, WorldRenderer wr, IEnumerable<IRenderable> r)
		{
			cloth ??= TwinOf(self, "-cloth");
			camo ??= TwinOf(self, self.World.WorldActor.TraitOrDefault<TgmcCamo>()?.Suffix);
			if (owner != self.Owner)
			{
				// The colour at full brightness: a dark player colour would otherwise black the unit out.
				owner = self.Owner;
				var c = owner.Color;
				var max = System.Math.Max(1, System.Math.Max((int)c.R, System.Math.Max((int)c.G, (int)c.B)));
				var s = info.Strength / 100f;
				tint = new Vector3(1 - s) + new Vector3((float)c.R / max, (float)c.G / max, (float)c.B / max) * s;
			}

			var armor = cloth.Count > 0 ? wr.Palette(info.ArmorPalette + owner.InternalName) : null;
			foreach (var a in r)
			{
				if (a is not SpriteRenderable sr || sr.IsDecoration)
					yield return a;
				else if (cloth.Count == 0 && camo.Count == 0)
					yield return sr.WithTint(sr.Tint * tint, sr.TintModifiers);
				else
				{
					yield return a;
					var sprite = (Sprite)SpriteField.GetValue(sr);
					if (camo.TryGetValue(sprite, out var worn))
						yield return Over(sr, worn, 1, sr.Palette);

					// The cloth sheet is indexed: its pixels are slots of the owner's armour palette, so it is drawn through it.
					if (cloth.TryGetValue(sprite, out var over))
						yield return Over(sr, over, 2, armor);
				}
			}
		}

		IEnumerable<Rectangle> IRenderModifier.ModifyScreenBounds(Actor self, WorldRenderer wr, IEnumerable<Rectangle> r) { return r; }
	}

	[TraitLocation(SystemActors.World | SystemActors.EditorWorld)]
	[Desc("The marines' camo for this map, as TGMC picks it from its map config (\"armor\"): standard armour and helmets are drawn from the " +
		"\"<image>-camo-<Style>\" sheets. An empty Style keeps the plain set (TGMC's desert, urban and default maps).")]
	public class TgmcCamoInfo : TraitInfo
	{
		public readonly string Style = "jungle";

		public override object Create(ActorInitializer init) { return new TgmcCamo(this); }
	}

	public class TgmcCamo
	{
		public readonly string Suffix;

		public TgmcCamo(TgmcCamoInfo info) { Suffix = string.IsNullOrEmpty(info.Style) ? null : "-camo-" + info.Style; }
	}

	[TraitLocation(SystemActors.World | SystemActors.EditorWorld)]
	[Desc("One armour palette per player, as TGMC colours armour: its colourable pieces are a five-shade ramp that a gradient map fills from one " +
		"of its ARMOR_PALETTE_* sets. The player's colour picks the set (Presets first, else the set whose bright shade is nearest in hue). " +
		"Slots 1 to 16 run along the ramp; 17 to 32 are the same a shade darker, for arm and leg pieces.")]
	public class TgmcArmorPaletteInfo : TraitInfo
	{
		public readonly string BaseName = "tgmcarmor";

		[Desc("TGMC's armour palettes: name and five hex colours, dark to light, separated by commas.")]
		public readonly Dictionary<string, string> Palettes = [];

		[Desc("Player colours (hex, upper case) that take a named palette outright: the lobby's squad colours take their squad's.")]
		public readonly Dictionary<string, string> Presets = [];

		[Desc("How bright the arm and leg slots are, in percent of the chest shade.")]
		public readonly int LimbShade = 80;

		public override object Create(ActorInitializer init) { return new TgmcArmorPalette(this); }
	}

	public class TgmcArmorPalette : ILoadsPlayerPalettes
	{
		static readonly Color[] Fallback = Parse("181928, 2c2f34, 4b4f56, 6b7478, 9faaac");
		readonly TgmcArmorPaletteInfo info;

		public TgmcArmorPalette(TgmcArmorPaletteInfo info) { this.info = info; }

		static Color[] Parse(string ramp)
		{
			return ramp.Split(['#', ',', ' '], System.StringSplitOptions.RemoveEmptyEntries).Select(h => Color.FromArgb(
				System.Convert.ToInt32(h[..2], 16), System.Convert.ToInt32(h.Substring(2, 2), 16), System.Convert.ToInt32(h.Substring(4, 2), 16))).ToArray();
		}

		// Colours compared by their shape, not their brightness: each divided by its strongest channel.
		static Vector3 Hue(Color c)
		{
			var max = System.Math.Max(1f, System.Math.Max(c.R, System.Math.Max(c.G, (float)c.B)));
			return new Vector3(c.R / max, c.G / max, c.B / max);
		}

		public Color[] RampFor(Color player)
		{
			var hex = $"{player.R:X2}{player.G:X2}{player.B:X2}";
			if (info.Presets.TryGetValue(hex, out var name) && info.Palettes.TryGetValue(name, out var preset))
				return Parse(preset);

			return info.Palettes.Values.Select(Parse).Where(p => p.Length == 5)
				.OrderBy(p => Vector3.DistanceSquared(Hue(p[3]), Hue(player))).FirstOrDefault() ?? Fallback;
		}

		void ILoadsPlayerPalettes.LoadPlayerPalettes(WorldRenderer wr, string playerName, Color playerColor, bool replaceExisting)
		{
			var ramp = RampFor(playerColor);
			var colors = new uint[256];
			var shade = info.LimbShade / 100f;
			for (var i = 0; i < 16; i++)
			{
				// Slot 1 + i sits at i / 15 of the way along the five shades.
				var x = i / 15f * 4;
				var k = System.Math.Min(3, (int)x);
				var t = x - k;
				var r = ramp[k].R + (ramp[k + 1].R - ramp[k].R) * t;
				var g = ramp[k].G + (ramp[k + 1].G - ramp[k].G) * t;
				var b = ramp[k].B + (ramp[k + 1].B - ramp[k].B) * t;
				colors[1 + i] = (uint)Color.FromArgb((int)r, (int)g, (int)b).ToArgb();
				colors[17 + i] = (uint)Color.FromArgb((int)(r * shade), (int)(g * shade), (int)(b * shade)).ToArgb();
			}

			wr.AddPalette(info.BaseName + playerName, new ImmutablePalette(colors), false, replaceExisting);
		}
	}
}
