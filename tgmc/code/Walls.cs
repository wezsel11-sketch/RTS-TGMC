#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
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
		public readonly string DustImage = "fx-dust-tile";
		public readonly string DustSequence = "dust";

		public override object Create(ActorInitializer init) { return new DestructibleWalls(init.Self, this); }
	}

	public class DestructibleWalls : IWorldLoaded
	{
		readonly DestructibleWallsInfo info;
		readonly Dictionary<CPos, int> health = [];

		public DestructibleWalls(Actor self, DestructibleWallsInfo info) { this.info = info; }

		void IWorldLoaded.WorldLoaded(World w, OpenRA.Graphics.WorldRenderer wr)
		{
			var map = w.Map;
			foreach (var cell in map.AllCells)
				if (info.Health.TryGetValue(map.GetTerrainInfo(cell).Type, out var hp))
					health[cell] = hp;
		}

		public void Hit(World world, CPos cell, int damage)
		{
			if (damage <= 0 || !health.TryGetValue(cell, out var hp))
				return;

			hp -= damage;
			if (hp > 0)
			{
				health[cell] = hp;
				return;
			}

			health.Remove(cell);
			var random = world.SharedRandom;
			world.Map.Tiles[cell] = new TerrainTile((ushort)info.Rubble[random.Next(info.Rubble.Length)], 0);
			Fx.Sprite(world, world.Map.CenterOfCell(cell), info.DustImage, info.DustSequence, "effect");
			Fx.Sound(world, world.Map.CenterOfCell(cell), info.Sounds);
		}
	}
}

namespace OpenRA.Mods.TGMC.Warheads
{
	using System;
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
