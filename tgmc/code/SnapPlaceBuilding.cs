#region Copyright & License Information
/*
 * Copyright (c) The OpenRA Developers and Contributors
 * This file is part of OpenRA, which is free software. It is made
 * available to you under the terms of the GNU General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version. For more
 * information, see COPYING.
 */
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Graphics;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Orders;
using OpenRA.Mods.Common.Traits;
using OpenRA.Orders;
using OpenRA.Primitives;
using OpenRA.Traits;
using OpenRA.Widgets;

namespace OpenRA.Mods.TGMC.Orders
{
	public class SnapPlaceBuildingOrderGenerator : IOrderGenerator
	{
		readonly string worldDefaultCursor = ChromeMetrics.Get<string>("WorldDefaultCursor");

		sealed class VariantWrapper
		{
			public readonly ActorInfo ActorInfo;
			public readonly BuildingInfo BuildingInfo;
			public readonly PlugInfo PlugInfo;
			public readonly LineBuildInfo LineBuildInfo;
			public readonly IPlaceBuildingPreview Preview;

			public VariantWrapper(WorldRenderer wr, ProductionQueue queue, ActorInfo ai)
			{
				ActorInfo = ai;
				BuildingInfo = ActorInfo.TraitInfo<BuildingInfo>();
				PlugInfo = ActorInfo.TraitInfoOrDefault<PlugInfo>();
				LineBuildInfo = ActorInfo.TraitInfoOrDefault<LineBuildInfo>();

				var previewGeneratorInfo = ActorInfo.TraitInfoOrDefault<IPlaceBuildingPreviewGeneratorInfo>();
				if (previewGeneratorInfo != null)
				{
					string faction;
					var buildableInfo = ActorInfo.TraitInfoOrDefault<BuildableInfo>();
					if (buildableInfo != null && buildableInfo.ForceFaction != null)
						faction = buildableInfo.ForceFaction;
					else
					{
						var mostLikelyProducer = queue.MostLikelyProducer();
						faction = mostLikelyProducer.Trait != null ? mostLikelyProducer.Trait.Faction : queue.Actor.Owner.Faction.InternalName;
					}

					var td = new TypeDictionary()
					{
						new FactionInit(faction),
						new OwnerInit(queue.Actor.Owner),
					};

					foreach (var api in ActorInfo.TraitInfos<IActorPreviewInitInfo>())
						foreach (var o in api.ActorPreviewInits(ActorInfo, ActorPreviewType.PlaceBuilding))
							td.Add(o);

					Preview = previewGeneratorInfo.CreatePreview(wr, ActorInfo, td);
				}
			}
		}

		readonly World world;
		protected readonly ProductionQueue Queue;
		readonly PlaceBuildingInfo placeBuildingInfo;
		readonly Viewport viewport;
		readonly VariantWrapper[] variants;
		readonly GameSettings gameSettings;
		int variant;

		public SnapPlaceBuildingOrderGenerator(ProductionQueue queue, string name, WorldRenderer worldRenderer)
		{
			Queue = queue;
			world = queue.Actor.World;
			placeBuildingInfo = queue.Actor.Owner.PlayerActor.Info.TraitInfo<PlaceBuildingInfo>();
			viewport = worldRenderer.Viewport;
			gameSettings = Game.Settings.Game;

			if (gameSettings.MouseControlStyle == MouseControlStyle.Classic)
				world.Selection.Clear();

			var variants = new List<VariantWrapper>()
			{
				new(worldRenderer, queue, world.Map.Rules.Actors[name])
			};

			foreach (var v in variants[0].ActorInfo.TraitInfos<PlaceBuildingVariantsInfo>())
				foreach (var a in v.Actors)
					variants.Add(new VariantWrapper(worldRenderer, queue, world.Map.Rules.Actors[a]));

			this.variants = variants.ToArray();
		}

		public MouseButton ActionButton => gameSettings.ResolveActionButton(MouseActionType.PlaceBuilding);

		static PlaceBuildingCellType MakeCellType(bool valid, bool lineBuild = false)
		{
			var cell = valid ? PlaceBuildingCellType.Valid : PlaceBuildingCellType.Invalid;
			if (lineBuild)
				cell |= PlaceBuildingCellType.LineBuild;

			return cell;
		}

		public IEnumerable<Order> Order(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			var actionButton = gameSettings.ResolveActionButton(MouseActionType.PlaceBuilding);
			var cancelButton = gameSettings.ResolveCancelButton(MouseActionType.PlaceBuilding);
			if ((mi.Button == actionButton && mi.Event == MouseInputEvent.Down) || (mi.Button == cancelButton && mi.Event == MouseInputEvent.Up))
			{
				if (mi.Button == cancelButton)
					world.CancelInputMode();

				var ret = InnerOrder(world, cell, mi).ToArray();

				// If there was a successful placement order
				if (ret.Any(o =>
						o.OrderString == "PlaceBuilding"
						|| o.OrderString == "LineBuild"
						|| o.OrderString == "PlacePlug"))
					world.CancelInputMode();

				return ret;
			}

			return [];
		}

		// Where the cursor puts the building's top-left corner.
		CPos RawTopLeft
		{
			get
			{
				var offsetPos = Viewport.LastMousePos;
				if (variants[variant].Preview != null)
					offsetPos = viewport.WorldToViewPx(viewport.ViewToWorldPx(offsetPos) + variants[variant].Preview.TopLeftScreenOffset);

				return viewport.ViewToWorld(offsetPos);
			}
		}

		const int SnapRadius = 4;
		CPos snapRaw;
		CPos snapResult;
		int snapVariant = -1;
		int snapTick = -100;

		// Where the building will actually go: the cursor's cell if the building fits there, otherwise the nearest cell
		// within a few cells where it does. Walls and plugs are placed exactly where you point.
		CPos TopLeft
		{
			get
			{
				var raw = RawTopLeft;
				var active = variants[variant];
				if (active.PlugInfo != null || active.LineBuildInfo != null)
					return raw;

				// The search is not free, so reuse the answer for a few ticks while the cursor stays put.
				if (raw == snapRaw && variant == snapVariant && world.WorldTick - snapTick < 6)
					return snapResult;

				snapRaw = raw;
				snapVariant = variant;
				snapTick = world.WorldTick;
				snapResult = Snap(raw, active);
				return snapResult;
			}
		}

		bool Fits(CPos cell, VariantWrapper v)
		{
			return world.CanPlaceBuilding(cell, v.ActorInfo, v.BuildingInfo, null)
				&& v.BuildingInfo.IsCloseEnoughToBase(world, Queue.Actor.Owner, v.ActorInfo, cell);
		}

		CPos Snap(CPos raw, VariantWrapper v)
		{
			if (!world.Map.Contains(raw) || Fits(raw, v))
				return raw;

			var best = raw;
			var bestDistance = int.MaxValue;
			for (var dx = -SnapRadius; dx <= SnapRadius; dx++)
			{
				for (var dy = -SnapRadius; dy <= SnapRadius; dy++)
				{
					var distance = dx * dx + dy * dy;
					if (distance == 0 || distance >= bestDistance)
						continue;

					var cell = raw + new CVec(dx, dy);
					if (world.Map.Contains(cell) && Fits(cell, v))
					{
						best = cell;
						bestDistance = distance;
					}
				}
			}

			return best;
		}

		protected virtual IEnumerable<Order> InnerOrder(World world, CPos cell, MouseInput mi)
		{
			if (world.Paused)
				yield break;

			var owner = Queue.Actor.Owner;
			var ai = variants[variant].ActorInfo;
			var bi = variants[variant].BuildingInfo;
			var notification = Queue.Info.CannotPlaceAudio ?? placeBuildingInfo.CannotPlaceNotification;

			if (mi.Button == ActionButton)
			{
				var orderType = "PlaceBuilding";
				var topLeft = TopLeft;

				var plugInfo = ai.TraitInfoOrDefault<PlugInfo>();
				if (plugInfo != null)
				{
					orderType = "PlacePlug";
					if (!AcceptsPlug(topLeft, plugInfo))
					{
						Game.Sound.PlayNotification(world.Map.Rules, owner, "Speech", notification, owner.Faction.InternalName);
						TextNotificationsManager.AddTransientLine(owner, placeBuildingInfo.CannotPlaceTextNotification);

						yield break;
					}
				}
				else
				{
					if (!world.CanPlaceBuilding(topLeft, ai, bi, null)
						|| !bi.IsCloseEnoughToBase(world, owner, ai, topLeft))
					{
						foreach (var order in ClearBlockersOrders(topLeft))
							yield return order;

						Game.Sound.PlayNotification(world.Map.Rules, owner, "Speech", notification, owner.Faction.InternalName);
						TextNotificationsManager.AddTransientLine(owner, placeBuildingInfo.CannotPlaceTextNotification);

						yield break;
					}

					if (ai.HasTraitInfo<LineBuildInfo>() && !mi.Modifiers.HasModifier(Modifiers.Shift))
						orderType = "LineBuild";
				}

				placed = true;
				yield return new Order(orderType, owner.PlayerActor, Target.FromCell(world, topLeft), false)
				{
					// Building to place
					TargetString = variants[0].ActorInfo.Name,

					// Actor ID to associate with placement may be quite large, so it gets its own uint
					ExtraData = Queue.Actor.ActorID,

					// Actor variant will always be small enough to safely pack in a CPos
					ExtraLocation = new CPos(variant, 0),

					SuppressVisualFeedback = true
				};

				// Ctrl-click: queue another of the same building, and open the ghost again once it is ready.
				if (orderType == "PlaceBuilding" && mi.Modifiers.HasModifier(Modifiers.Ctrl))
				{
					OpenRA.Mods.TGMC.Traits.SnapPlacement.Repeat = (Queue, variants[0].ActorInfo.Name);
					yield return OpenRA.Order.StartProduction(Queue.Actor, variants[0].ActorInfo.Name, 1);
				}
				else
					OpenRA.Mods.TGMC.Traits.SnapPlacement.Repeat = null;
			}
		}

		void IOrderGenerator.Tick(World world)
		{
			if (Queue.AllQueued().All(i => !i.Done || i.Item != variants[0].ActorInfo.Name))
				world.CancelInputMode();

			foreach (var v in variants)
				v.Preview?.Tick();
		}

		void IOrderGenerator.SelectionChanged(World world, IEnumerable<Actor> selected) { }

		bool AcceptsPlug(CPos cell, PlugInfo plug)
		{
			foreach (var a in world.ActorMap.GetActorsAt(cell))
				foreach (var p in a.TraitsImplementing<Pluggable>())
					if (p.AcceptsPlug(plug.Type))
						return true;

			return false;
		}

		IEnumerable<IRenderable> IOrderGenerator.Render(WorldRenderer wr, World world) { yield break; }
		IEnumerable<IRenderable> IOrderGenerator.RenderAboveShroud(WorldRenderer wr, World world)
		{
			var topLeft = TopLeft;
			var footprint = new Dictionary<CPos, PlaceBuildingCellType>();
			var activeVariant = variants[variant];
			var actorInfo = activeVariant.ActorInfo;
			var buildingInfo = activeVariant.BuildingInfo;
			var plugInfo = activeVariant.PlugInfo;
			var lineBuildInfo = activeVariant.LineBuildInfo;
			var preview = activeVariant.Preview;
			var owner = Queue.Actor.Owner;

			if (plugInfo != null)
			{
				if (buildingInfo.Dimensions.X != 1 || buildingInfo.Dimensions.Y != 1)
					throw new InvalidOperationException("Plug requires a 1x1 sized Building");

				footprint.Add(topLeft, MakeCellType(AcceptsPlug(topLeft, plugInfo)));
			}
			else if (lineBuildInfo != null && owner.Shroud.IsExplored(topLeft))
			{
				// Linebuild for walls.
				if (buildingInfo.Dimensions.X != 1 || buildingInfo.Dimensions.Y != 1)
					throw new InvalidOperationException("LineBuild requires a 1x1 sized Building");

				if (!Game.GetModifierKeys().HasModifier(Modifiers.Shift))
				{
					var segmentInfo = actorInfo;
					var segmentBuildingInfo = buildingInfo;
					if (!string.IsNullOrEmpty(lineBuildInfo.SegmentType))
					{
						segmentInfo = world.Map.Rules.Actors[lineBuildInfo.SegmentType];
						segmentBuildingInfo = segmentInfo.TraitInfo<BuildingInfo>();
					}

					foreach (var t in BuildingUtils.GetLineBuildCells(world, topLeft, actorInfo, buildingInfo, owner))
					{
						var lineBuildable = world.IsCellBuildable(t.Cell, segmentInfo, segmentBuildingInfo);
						var lineCloseEnough = segmentBuildingInfo.IsCloseEnoughToBase(world, world.LocalPlayer, segmentInfo, t.Cell);
						footprint.Add(t.Cell, MakeCellType(lineBuildable && lineCloseEnough, true));
					}
				}

				var buildable = world.IsCellBuildable(topLeft, actorInfo, buildingInfo);
				var closeEnough = buildingInfo.IsCloseEnoughToBase(world, world.LocalPlayer, actorInfo, topLeft);
				footprint[topLeft] = MakeCellType(buildable && closeEnough);
			}
			else
			{
				var isCloseEnough = buildingInfo.IsCloseEnoughToBase(world, world.LocalPlayer, actorInfo, topLeft);
				foreach (var t in buildingInfo.Tiles(topLeft))
					footprint.Add(t, MakeCellType(isCloseEnough && world.IsCellBuildable(t, actorInfo, buildingInfo)));
			}

			return preview?.Render(wr, topLeft, footprint) ?? [];
		}

		IEnumerable<IRenderable> IOrderGenerator.RenderAnnotations(WorldRenderer wr, World world)
		{
			var topLeft = TopLeft;
			var active = variants[variant];
			var preview = active.Preview;
			foreach (var r in preview?.RenderAnnotations(wr, topLeft) ?? [])
				yield return r;

			// When even the nearest cell will not do, say why next to the ghost.
			if (active.PlugInfo != null || active.LineBuildInfo != null || !world.Map.Contains(topLeft) || Fits(topLeft, active))
				yield break;

			string reason;
			if (!world.CanPlaceBuilding(topLeft, active.ActorInfo, active.BuildingInfo, null))
				reason = "placement-blocked";
			else
				reason = Queue.Actor.Owner.Faction.InternalName == "xenos" ? "placement-too-far-xeno" : "placement-too-far-marine";

			if (Game.Renderer.Fonts.TryGetValue("Bold", out var font))
				yield return new TextAnnotationRenderable(font, world.Map.CenterOfCell(topLeft) - new WVec(0, 900, 0), 0,
					Color.FromArgb(255, 110, 90), FluentProvider.GetMessage(reason));
		}

		public virtual string GetCursor(World world, CPos cell, int2 worldPixel, MouseInput mi)
		{
			return worldDefaultCursor;
		}

		bool IOrderGenerator.HandleKeyPress(KeyInput e)
		{
			if (variants.Length > 0 && placeBuildingInfo.ToggleVariantKey.IsActivatedBy(e))
			{
				if (++variant >= variants.Length)
					variant = 0;

				return true;
			}

			return false;
		}

		bool placed;

		void IOrderGenerator.Deactivate()
		{
			// Backing out of the ghost (right-click, Esc) also ends a repeat run.
			if (!placed)
				OpenRA.Mods.TGMC.Traits.SnapPlacement.Repeat = null;
		}

		IEnumerable<Order> ClearBlockersOrders(CPos topLeft)
		{
			return AIUtils.ClearBlockersOrders(variants[variant].BuildingInfo.Tiles(topLeft).ToList(), Queue.Actor.Owner);
		}
	}
}


namespace OpenRA.Mods.TGMC.Traits
{
	using OpenRA.Mods.TGMC.Orders;

	[TraitLocation(SystemActors.World)]
	[Desc("Swaps the engine's building placement for one that snaps the ghost to the nearest cell where the building fits.")]
	public class SnapPlacementInfo : TraitInfo
	{
		public override object Create(ActorInitializer init) { return new SnapPlacement(); }
	}

	public class SnapPlacement : IWorldLoaded
	{
		/// <summary>Set by a Ctrl-click placement: the queue and building to keep placing.</summary>
		public static (ProductionQueue Queue, string Item)? Repeat;

		void IWorldLoaded.WorldLoaded(World w, WorldRenderer wr)
		{
			// The order generator may only change outside the simulation, so a widget does the swap on its own tick.
			var ticker = new OpenRA.Mods.Common.Widgets.LogicTickerWidget { OnTick = () => TakeOver(w, wr) };
			OpenRA.Widgets.Ui.Root.AddChild(ticker);
		}

		static void TakeOver(World world, WorldRenderer worldRenderer)
		{
			var player = world.LocalPlayer;
			if (player == null)
				return;

			if (Repeat is { } repeat)
			{
				var items = repeat.Queue.AllQueued().Where(i => i.Item == repeat.Item).ToList();
				if (items.Count == 0)
					Repeat = null;
				else if (items.Any(i => i.Done) && world.OrderGenerator?.GetType() != typeof(SnapPlaceBuildingOrderGenerator))
					world.OrderGenerator = new SnapPlaceBuildingOrderGenerator(repeat.Queue, repeat.Item, worldRenderer);

				return;
			}

			if (world.OrderGenerator?.GetType() != typeof(PlaceBuildingOrderGenerator))
				return;

			// The engine has just started placing a finished building: find which one, and take over.
			foreach (var queue in player.PlayerActor.TraitsImplementing<ProductionQueue>())
			{
				var done = queue.AllQueued().FirstOrDefault(i => i.Done && world.Map.Rules.Actors[i.Item].HasTraitInfo<BuildingInfo>());
				if (done == null)
					continue;

				world.OrderGenerator = new SnapPlaceBuildingOrderGenerator(queue, done.Item, worldRenderer);
				return;
			}
		}
	}
}
