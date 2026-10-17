#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Sight that stops at walls: the unit reveals only the cells it can see from where it stands, so rock and walls hide what is behind them. " +
		"Optionally limited to a cone in front of the unit (Cone, in degrees; 360 is all round).")]
	public class TgmcSightInfo : RevealsShroudInfo
	{
		[Desc("Width of the view cone in degrees, centred on the facing. 360 sees all round.")]
		public readonly int Cone = 360;

		[Desc("Cells this close are always seen, so a unit never stands blind next to itself.")]
		public readonly int AlwaysSeeCells = 1;

		[Desc("Sense through walls inside the cone instead of needing a clear line (the xenos: they sense the marines in front of them).")]
		public readonly bool ThroughWalls = false;

		public override object Create(ActorInitializer init) { return new TgmcSight(this); }
	}

	public class TgmcSight : RevealsShroud
	{
		readonly TgmcSightInfo sightInfo;

		public TgmcSight(TgmcSightInfo info)
			: base(info)
		{
			sightInfo = info;
		}

		protected override void AddCellsToPlayerShroud(Actor self, Player p, PPos[] uv)
		{
			var map = self.World.Map;
			var origin = self.Location;
			var facing = self.TraitOrDefault<IFacing>()?.Facing ?? WAngle.Zero;
			var forward = new WVec(0, -1024, 0).Rotate(WRot.FromYaw(facing));
			var cosHalf = Math.Cos(sightInfo.Cone / 2.0 * Math.PI / 180.0);
			var visible = uv.Where(puv =>
			{
				var cell = ((MPos)puv).ToCPos(map);
				var dx = cell.X - origin.X;
				var dy = cell.Y - origin.Y;
				if (Math.Max(Math.Abs(dx), Math.Abs(dy)) <= sightInfo.AlwaysSeeCells)
					return true;

				if (sightInfo.Cone < 360)
				{
					var to = map.CenterOfCell(cell) - self.CenterPosition;
					var len = Math.Sqrt((double)to.HorizontalLengthSquared);
					var fwd = Math.Sqrt((double)forward.HorizontalLengthSquared);
					if (len > 0 && (to.X * (double)forward.X + to.Y * (double)forward.Y) / (len * fwd) < cosHalf)
						return false;
				}

				return sightInfo.ThroughWalls || ClearLine(self.World, origin, cell);
			}).ToArray();

			base.AddCellsToPlayerShroud(self, p, visible);
		}

		// Walks the cells between the two from the unit's cell to the target and stops at rock and walls.
		static bool ClearLine(World world, CPos from, CPos to)
		{
			var dx = to.X - from.X;
			var dy = to.Y - from.Y;
			var steps = Math.Max(Math.Abs(dx), Math.Abs(dy));
			for (var i = 1; i < steps; i++)
			{
				var cell = new CPos(from.X + dx * i / steps, from.Y + dy * i / steps);
				var map = world.Map;
				if (!map.Contains(cell))
					return false;

				var type = map.GetTerrainInfo(cell).Type;
				if (type is "Rock" or "Wall" or "ReinforcedWall")
					return false;

				// A closed solid door stops the view too.
				if (world.ActorMap.GetActorsAt(cell).Any(a => a.TraitOrDefault<MapDoor>() is { BlocksSight: true }))
					return false;
			}

			return true;
		}
	}
}
