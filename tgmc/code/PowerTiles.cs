// Support powers as one tile per family (air, orbital, drops, support) under the minimap. The marines have 22 powers;
// the engine's SupportPowersWidget draws them as one column that runs off the screen.

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.TGMC.Traits;
using OpenRA.Primitives;
using OpenRA.Widgets;

namespace OpenRA.Mods.TGMC.Widgets
{
	public class PowerTilesWidget : Widget
	{
		[Desc("Panel drawn behind each tile. FactionSkinLogic swaps it for the faction's own.")]
		public string Background = "tgui-card";

		public readonly int2 TileSize = new(50, 38);
		public readonly int TileMargin = 2;
		public readonly string Font = "TinyBold";
		public readonly string HotkeyPrefix = "SupportPower";
		public readonly int HotkeyCount = 6;

		[FluentReference]
		public string ReadyText = "supportpowers-support-powers-palette.ready";

		[FluentReference]
		public string HoldText = "supportpowers-support-powers-palette.hold";

		readonly ModData modData;
		readonly WorldRenderer worldRenderer;
		readonly SupportPowerManager spm;
		readonly Dictionary<(string, string), Sprite> sprites = [];
		readonly List<(Rectangle Rect, List<SupportPowerInstance> Powers)> tiles = [];
		readonly List<(Rectangle Rect, SupportPowerInstance Power)> row = [];

		HotkeyReference[] hotkeys;
		SpriteFont font;
		int open = -1;
		SupportPowerInstance hovered;
		Rectangle eventBounds = Rectangle.Empty;

		public override Rectangle EventBounds => eventBounds;

		[ObjectCreator.UseCtor]
		public PowerTilesWidget(ModData modData, World world, WorldRenderer worldRenderer)
		{
			this.modData = modData;
			this.worldRenderer = worldRenderer;
			spm = world.LocalPlayer.PlayerActor.Trait<SupportPowerManager>();
		}

		public override void Initialize(WidgetArgs args)
		{
			base.Initialize(args);
			hotkeys = Exts.MakeArray(HotkeyCount, i => modData.Hotkeys[HotkeyPrefix + (i + 1).ToStringInvariant("D2")]);
			font = Game.Renderer.Fonts[Font];
			ReadyText = FluentProvider.GetMessage(ReadyText);
			HoldText = FluentProvider.GetMessage(HoldText);
		}

		// 0 air (the Condor's runs), 1 orbital, 2 drops, 3 everything else (smoke, sensor, bell, the hive's powers).
		static int Family(SupportPowerInstance p)
		{
			var order = p.Info.OrderName;
			if (order.StartsWith("Cas", StringComparison.Ordinal))
				return 0;

			if (order.StartsWith("Orbital", StringComparison.Ordinal) || order == "RailgunOrder")
				return 1;

			return p.Info is DropPodPowerInfo ? 2 : 3;
		}

		// Ready first, then the one that will be ready soonest; a power on hold goes last.
		static int Wait(SupportPowerInstance p)
		{
			return p.Active ? p.RemainingTicks : int.MaxValue;
		}

		public override void Tick()
		{
			var rb = RenderBounds;
			var step = TileSize.Y + TileMargin;
			tiles.Clear();
			foreach (var family in spm.Powers.Values.Where(p => !p.Disabled).GroupBy(Family).OrderBy(g => g.Key))
				tiles.Add((new Rectangle(rb.X, rb.Y + tiles.Count * step, TileSize.X, TileSize.Y),
					family.OrderBy(p => p.Info.SupportPowerPaletteOrder).ThenBy(p => p.Info.OrderName, StringComparer.Ordinal).ToList()));

			if (open >= tiles.Count)
				open = -1;

			row.Clear();
			if (open >= 0)
			{
				var tile = tiles[open];
				for (var i = 0; i < tile.Powers.Count; i++)
					row.Add((new Rectangle(tile.Rect.X - (i + 1) * (TileSize.X + TileMargin), tile.Rect.Y, TileSize.X, TileSize.Y), tile.Powers[i]));
			}

			eventBounds = tiles.Select(t => t.Rect).Concat(row.Select(r => r.Rect)).Union();
		}

		Sprite Icon(SupportPowerInstance p)
		{
			var key = (p.Info.IconImage, p.Info.Icon);
			if (!sprites.TryGetValue(key, out var sprite))
			{
				var icon = new Animation(worldRenderer.World, key.IconImage);
				icon.Play(key.Icon);
				sprites[key] = sprite = icon.Image;
			}

			return sprite;
		}

		void DrawTile(Rectangle rect, SupportPowerInstance p, string count)
		{
			WidgetUtils.DrawPanel(Background, rect);
			var centre = new int2(rect.X + rect.Width / 2, rect.Y + rect.Height / 2).ToVector2();
			WidgetUtils.DrawSpriteCentered(Icon(p), worldRenderer.Palette(p.Info.IconPalette), centre);

			// A ready power pulses amber, about once a second.
			if (p.Ready)
				WidgetUtils.FillRectWithColor(rect, Color.FromArgb(30 + (int)(30 * Math.Sin(Game.RunTime / 160.0)), 255, 196, 84));

			var text = p.Ready ? ReadyText : !p.Active ? HoldText : WidgetUtils.FormatTime(p.RemainingTicks, worldRenderer.World.Timestep);
			font.DrawTextWithContrast(text, centre - font.Measure(text).ToVector2() / 2, Color.White, Color.Black, 1);
			if (count != null)
				font.DrawTextWithContrast(count, new int2(rect.X + 3, rect.Y + 1).ToVector2(), Color.FromArgb(255, 196, 84), Color.Black, 1);
		}

		public override void Draw()
		{
			foreach (var (rect, powers) in tiles)
				DrawTile(rect, powers.MinBy(Wait), powers.Count > 1 ? $"{powers.Count(p => p.Ready)}/{powers.Count}" : null);

			foreach (var (rect, power) in row)
				DrawTile(rect, power, null);

			// The name of the power under the mouse, above the open row (its right end sits over the tile).
			if (hovered != null && row.Count > 0)
			{
				var name = hovered.Name;
				var right = row[0].Rect.Right;
				font.DrawTextWithContrast(name, new int2(right - font.Measure(name).X, row[0].Rect.Y - font.Measure(name).Y - 3).ToVector2(), Color.White, Color.Black, 1);
			}
		}

		// The engine's SupportPowersWidget.ClickIcon: target the power, or say why not.
		void Fire(SupportPowerInstance p)
		{
			open = -1;
			if (p.Active)
			{
				p.Target();
				return;
			}

			var owner = spm.Self.Owner;
			Game.Sound.PlayToPlayer(SoundType.UI, owner, p.Info.InsufficientPowerSound);
			Game.Sound.PlayNotification(spm.Self.World.Map.Rules, owner, "Speech", p.Info.InsufficientPowerSpeechNotification, owner.Faction.InternalName);
			TextNotificationsManager.AddTransientLine(owner, p.Info.InsufficientPowerTextNotification);
		}

		// A family of one fires; a larger one opens its row, or closes it.
		public void ClickTile(int index)
		{
			if (index >= tiles.Count)
				return;

			if (tiles[index].Powers.Count == 1)
				Fire(tiles[index].Powers[0]);
			else
				open = open == index ? -1 : index;
		}

		public override bool HandleKeyPress(KeyInput e)
		{
			if (e.Event != KeyInputEvent.Down)
				return false;

			for (var i = 0; i < Math.Min(hotkeys.Length, tiles.Count); i++)
				if (hotkeys[i].IsActivatedBy(e))
				{
					ClickTile(i);
					return true;
				}

			return false;
		}

		public override void MouseExited()
		{
			hovered = null;
			open = -1;
		}

		public override bool HandleMouseInput(MouseInput mi)
		{
			var inRow = row.FindIndex(r => r.Rect.Contains(mi.Location));
			if (mi.Event == MouseInputEvent.Move)
			{
				hovered = inRow >= 0 ? row[inRow].Power : null;
				return false;
			}

			if (mi.Event != MouseInputEvent.Down)
				return false;

			var tile = tiles.FindIndex(t => t.Rect.Contains(mi.Location));
			if (inRow >= 0)
				Fire(row[inRow].Power);
			else if (tile >= 0)
				ClickTile(tile);

			return inRow >= 0 || tile >= 0;
		}
	}
}
