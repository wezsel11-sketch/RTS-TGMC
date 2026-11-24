#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.GameRules;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.World)]
	[Desc("The walls of the converted TGMC maps can be shot to rubble. Wall tiles carry the terrain type Wall (plain walls) or ReinforcedWall; each such cell has hit points, " +
		"heavy weapons damage it (the DamageWalls warhead), and a cell that runs out turns into rubble that units can walk over.")]
	public class DestructibleWallsInfo : TraitInfo
	{
		[Desc("Hit points of a cell of each wall terrain type.")]
		public readonly Dictionary<string, int> Health = new() { { "Wall", 500 }, { "ReinforcedWall", 1500 } };

		[Desc("Tileset template ids the rubble is made of, one picked at random (a one-tile template of walkable ground).")]
		public readonly int[] Rubble = [4];

		public readonly string[] Sounds = [];
		[WeaponReference]
		[Desc("Goes off where a wall cell falls: looks only (flying rubble), no damage.")]
		public readonly string BreakWeapon = null;

		public readonly string DustImage = "fx-dust-tile";
		public readonly string DustSequence = "dust";

		[Desc("TGMC's wall damage overlay (overlay_damage of icons/turf/walls.dmi), drawn over a damaged cell in DamageSteps steps of opacity.")]
		public readonly string DamageImage = "fx-wall-damage";
		public readonly string DamageSequence = "idle";
		public readonly string DamagePalette = "effect";
		public readonly int DamageSteps = 8;

		public override object Create(ActorInitializer init) { return new DestructibleWalls(init.Self, this); }
	}

	public class DestructibleWalls : IWorldLoaded, IRenderAboveWorld
	{
		readonly DestructibleWallsInfo info;
		readonly Dictionary<CPos, int> health = [];

		// Damaged cells -> how far gone (1 to DamageSteps), as update_overlays in TGMC's walls.dm.
		readonly Dictionary<CPos, int> damaged = [];

		// Render only: the steps the render player last saw, so the overlay does not show live damage through fog.
		readonly Dictionary<CPos, int> seen = [];
		OpenRA.Graphics.Sprite damageSprite;

		public DestructibleWalls(Actor self, DestructibleWallsInfo info) { this.info = info; }

		void IWorldLoaded.WorldLoaded(World w, OpenRA.Graphics.WorldRenderer wr)
		{
			var map = w.Map;
			foreach (var cell in map.AllCells)
				if (info.Health.TryGetValue(map.GetTerrainInfo(cell).Type, out var hp))
					health[cell] = hp;

			if (!string.IsNullOrEmpty(info.DamageImage))
				damageSprite = map.Sequences.GetSequence(info.DamageImage, info.DamageSequence).GetSprite(0);
		}

		public void Hit(World world, CPos cell, int damage)
		{
			if (damage <= 0 || !health.TryGetValue(cell, out var hp))
				return;

			hp -= damage;
			if (hp > 0)
			{
				health[cell] = hp;
				var full = info.Health[world.Map.GetTerrainInfo(cell).Type];
				damaged[cell] = Math.Min(info.DamageSteps, (full - hp) * info.DamageSteps / full + 1);
				return;
			}

			health.Remove(cell);
			damaged.Remove(cell);
			var random = world.SharedRandom;
			world.Map.Tiles[cell] = new TerrainTile((ushort)info.Rubble[random.Next(info.Rubble.Length)], 0);
			Fx.Sprite(world, world.Map.CenterOfCell(cell), info.DustImage, info.DustSequence, "effect");
			Fx.Sound(world, world.Map.CenterOfCell(cell), info.Sounds);
			if (info.BreakWeapon != null)
				world.Map.Rules.Weapons[info.BreakWeapon.ToLowerInvariant()].Impact(Target.FromPos(world.Map.CenterOfCell(cell)), world.WorldActor);
		}

		// Drawn before the shroud, so an unexplored wall shows nothing; a fogged cell shows the last step the render player saw.
		void IRenderAboveWorld.RenderAboveWorld(Actor self, OpenRA.Graphics.WorldRenderer wr)
		{
			if (damageSprite == null || (damaged.Count == 0 && seen.Count == 0))
				return;

			var shown = damaged;
			if (self.World.RenderPlayer != null)
			{
				foreach (var cell in damaged.Keys.Union(seen.Keys).ToList())
				{
					if (self.World.FogObscures(cell))
						continue;

					if (damaged.TryGetValue(cell, out var now))
						seen[cell] = now;
					else
						seen.Remove(cell);
				}

				shown = seen;
			}

			var palette = wr.Palette(info.DamagePalette);
			var tl = wr.Viewport.TopLeft;
			var br = wr.Viewport.BottomRight;
			foreach (var (cell, step) in shown)
			{
				var pos = self.World.Map.CenterOfCell(cell);
				var px = wr.ScreenPxPosition(pos);
				if (px.X < tl.X - 32 || px.Y < tl.Y - 32 || px.X > br.X + 32 || px.Y > br.Y + 32)
					continue;

				new OpenRA.Graphics.SpriteRenderable(damageSprite, pos, WVec.Zero, 0, palette, 1f, step / (float)info.DamageSteps,
					System.Numerics.Vector3.One, OpenRA.Graphics.TintModifiers.None, false).PrepareRender(wr).Render(wr);
			}
		}
	}
}

namespace OpenRA.Mods.TGMC.Warheads
{
	using OpenRA.Mods.TGMC.Traits;

	[Desc("Damages the destructible wall cells (see DestructibleWalls) around the impact: Damage at the middle, less toward the edge of Radius.")]
	public class DamageWallsWarhead : Warhead
	{
		public readonly int Damage = 0;
		public readonly WDist Radius = new(2 * 1024);

		public override void DoImpact(in Target target, WarheadArgs args)
		{
			var world = args.SourceActor?.World;
			var walls = world?.WorldActor.TraitOrDefault<DestructibleWalls>();
			if (walls == null || target.Type == TargetType.Invalid)
				return;

			var centre = world.Map.CellContaining(target.CenterPosition);
			var cells = Math.Max(1, Radius.Length / 1024);
			for (var dx = -cells; dx <= cells; dx++)
			{
				for (var dy = -cells; dy <= cells; dy++)
				{
					var cell = new CPos(centre.X + dx, centre.Y + dy);
					if (!world.Map.Contains(cell))
						continue;

					var distance = (world.Map.CenterOfCell(cell) - target.CenterPosition).HorizontalLength;
					if (distance > Radius.Length)
						continue;

					walls.Hit(world, cell, Damage * (Radius.Length - distance) / Radius.Length);
				}
			}
		}
	}
}
