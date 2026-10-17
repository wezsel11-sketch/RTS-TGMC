#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Effects;
using OpenRA.GameRules;
using OpenRA.Graphics;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Warheads
{
	[Desc("A blast that spreads from tile to tile. At the impact it does full Damage; the wave then rolls outward one ring of tiles every RingDelay ticks, " +
		"hurting what stands in each tile a little less than the one before and kicking up dust. Rock stops it, a building weakens it (BlockCost cells " +
		"of reach), so a wall shields what is behind it and the wave bends around corners.")]
	public class ShockwaveWarhead : DamageWarhead
	{
		[Desc("How far the wave reaches, in cells.")]
		public readonly int Radius = 8;

		[Desc("Ticks between one ring of tiles and the next.")]
		public readonly int RingDelay = 2;

		[Desc("Cells of reach a building in the way costs the wave.")]
		public readonly int BlockCost = 4;

		[Desc("Damage at the edge as a percent of the damage at the middle.")]
		public readonly int EdgePercent = 5;

		[Desc("Dust kicked up in a tile as the wave passes (an image and sequence, as in CreateEffect). Percent chance per tile.")]
		public readonly string DustImage = null;
		public readonly string DustSequence = "dust";
		public readonly string DustPalette = "effect";
		public readonly int DustChance = 30;

		public override bool IsValidAgainst(Actor victim, Actor firedBy)
		{
			if (!OpenRA.Mods.TGMC.Options.Enabled(firedBy.World, OpenRA.Mods.TGMC.Options.FriendlyFire, true)
				&& firedBy.Owner.RelationshipWith(victim.Owner) == PlayerRelationship.Ally)
				return false;

			return base.IsValidAgainst(victim, firedBy);
		}

		public override void DoImpact(in Target target, WarheadArgs args)
		{
			if (args.SourceActor == null || target.Type == TargetType.Invalid)
				return;

			var world = args.SourceActor.World;
			var at = target.CenterPosition;
			world.AddFrameEndTask(w => w.Add(new Shockwave(this, at, args)));
		}

		protected override void DoImpact(WPos pos, Actor firedBy, WarheadArgs args) { }


		public void Hurt(Actor victim, Actor firedBy, int percent, WarheadArgs args)
		{
			if (!IsValidAgainst(victim, firedBy))
				return;

			// A strong enough blast throws the unit away from its centre, like the marines' and xenos' throws (see KnockbackWarhead).
			if (percent >= 30 && args.Source != null)
				KnockbackWarhead.Throw(victim, firedBy, args.Source.Value, new WDist(percent >= 70 ? 2048 : 1024), 10, new WDist(512), 0, 0, default);

			var shape = (HitShape)victim.EnabledTargetablePositions.MinByOrDefault(t => t is HitShape h ? h.DistanceFromEdge(victim, victim.CenterPosition) : WDist.MaxValue);
			if (shape == null)
				return;

			var damage = OpenRA.Mods.Common.Util.ApplyPercentageModifiers(Damage * percent / 100, args.DamageModifiers.Append(DamageVersus(victim, shape, args)));
			if (damage > 0)
				victim.InflictDamage(firedBy, new Damage(damage, DamageTypes));
		}
	}

	sealed class Shockwave : IEffect
	{
		readonly ShockwaveWarhead info;
		readonly WarheadArgs args;
		readonly World world;
		readonly Actor firedBy;
		readonly Dictionary<int, List<(CPos Cell, float Cost)>> rings = [];
		readonly HashSet<Actor> hit = [];
		int tick;
		int last;

		public Shockwave(ShockwaveWarhead info, WPos at, WarheadArgs args)
		{
			this.info = info;
			this.args = args;
			firedBy = args.SourceActor;
			world = firedBy.World;
			Spread(world.Map.CellContaining(at));
		}

		// Dijkstra over the cells: rock cannot be entered, a building costs extra reach, and the cost of a cell decides its ring and its damage.
		void Spread(CPos start)
		{
			var map = world.Map;
			var best = new Dictionary<CPos, float> { [start] = 0 };
			var open = new List<(CPos Cell, float Cost)> { (start, 0) };
			while (open.Count > 0)
			{
				var index = 0;
				for (var i = 1; i < open.Count; i++)
					if (open[i].Cost < open[index].Cost)
						index = i;

				var (cell, cost) = open[index];
				open.RemoveAt(index);
				if (cost > best[cell])
					continue;

				var ring = (int)cost;
				if (!rings.TryGetValue(ring, out var list))
					rings[ring] = list = [];

				list.Add((cell, cost));
				last = Math.Max(last, ring);

				for (var dx = -1; dx <= 1; dx++)
				{
					for (var dy = -1; dy <= 1; dy++)
					{
						if (dx == 0 && dy == 0)
							continue;

						var next = new CPos(cell.X + dx, cell.Y + dy);
						if (!map.Contains(next) || map.GetTerrainInfo(next).Type is "Rock" or "Wall" or "ReinforcedWall")
							continue;

						var step = dx != 0 && dy != 0 ? 1.414f : 1f;
						if (world.ActorMap.GetActorsAt(next).Any(a => a.Info.HasTraitInfo<BuildingInfo>() && a.Info.Name != "weeds"))
							step += info.BlockCost;

						var total = cost + step;
						if (total > info.Radius || (best.TryGetValue(next, out var known) && known <= total))
							continue;

						best[next] = total;
						open.Add((next, total));
					}
				}
			}
		}

		void IEffect.Tick(World w)
		{
			var ring = tick / Math.Max(1, info.RingDelay);
			if (tick % Math.Max(1, info.RingDelay) == 0 && rings.TryGetValue(ring, out var cells))
			{
				foreach (var (cell, cost) in cells)
				{
					var percent = Math.Max(info.EdgePercent, 100 - (int)(cost * (100 - info.EdgePercent) / info.Radius));
					foreach (var victim in world.ActorMap.GetActorsAt(cell).ToList())
					{
						if (victim.IsDead || !victim.IsInWorld || !hit.Add(victim))
							continue;

						info.Hurt(victim, firedBy, percent, args);
					}

					if (info.DustImage != null && world.SharedRandom.Next(100) < info.DustChance)
						Fx.Sprite(world, world.Map.CenterOfCell(cell), info.DustImage, info.DustSequence, info.DustPalette);
				}
			}

			if (++tick > (last + 1) * Math.Max(1, info.RingDelay))
				world.AddFrameEndTask(x => x.Remove(this));
		}

		IEnumerable<IRenderable> IEffect.Render(WorldRenderer wr) { yield break; }
	}
}
