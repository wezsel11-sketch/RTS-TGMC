using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Scripting;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("Remembers where this player has seen enemy strength, on a coarse grid that fades over time, and which of its own actors " +
		"were attacked lately. It ticks on its own, without a bot, so mission scripts (Lua: ThreatNear) and bot modules can both read it. " +
		"Only what the player saw counts, unless FullVision is set.")]
	public class ThreatMemoryInfo : ConditionalTraitInfo
	{
		[Desc("Ticks between looks at the map.")]
		public readonly int Interval = 25;

		[Desc("Map cells per grid square, along each side.")]
		public readonly int CellSize = 4;

		[Desc("Share of each square's remembered strength kept per look (percent), so an old sighting fades.")]
		public readonly int FadePercent = 90;

		[Desc("Count every enemy actor, seen or not. For mission enemies that know the whole map; skirmish bots leave it off.")]
		public readonly bool FullVision = false;

		[Desc("Defensive actor types: they count DefenceWeight percent of their cost.")]
		public readonly string[] Defences = [];

		[Desc("How much a defensive actor counts, in percent of its cost.")]
		public readonly int DefenceWeight = 200;

		[Desc("Ticks an attack on one of this player's actors stays recent.")]
		public readonly int AttackMemory = 250;

		[Desc("SafePath: remembered strength (near a square, within two squares) that doubles the cost of walking through it.")]
		public readonly int StepCostValue = 50;

		public override object Create(ActorInitializer init) { return new ThreatMemory(init.Self, this); }
	}

	public class ThreatMemory : ConditionalTrait<ThreatMemoryInfo>, ITick
	{
		readonly World world;
		readonly Player player;
		readonly int cols, rows;
		readonly float[,] grid;
		readonly Dictionary<Actor, (Actor Attacker, int Tick)> attacks = [];
		int countdown;

		public ThreatMemory(Actor self, ThreatMemoryInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
			cols = world.Map.MapSize.Width / info.CellSize + 1;
			rows = world.Map.MapSize.Height / info.CellSize + 1;
			grid = new float[cols, rows];
		}

		int Value(ActorInfo info)
		{
			var cost = info.TraitInfoOrDefault<ValuedInfo>()?.Cost ?? 0;
			return Info.Defences.Contains(info.Name) ? cost * Info.DefenceWeight / 100 : cost;
		}

		(int X, int Y) Square(CPos cell)
		{
			return (Math.Clamp(cell.X / Info.CellSize, 0, cols - 1), Math.Clamp(cell.Y / Info.CellSize, 0, rows - 1));
		}

		bool SquareVisible(int x, int y)
		{
			var c = new CPos(Math.Min(x * Info.CellSize + Info.CellSize / 2, world.Map.MapSize.Width - 1), Math.Min(y * Info.CellSize + Info.CellSize / 2, world.Map.MapSize.Height - 1));
			return player.Shroud.IsVisible(c);
		}

		bool IsEnemy(Player other) { return other != null && player.RelationshipWith(other) == PlayerRelationship.Enemy; }

		void ITick.Tick(Actor self)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;
			var now = new float[cols, rows];
			foreach (var a in world.Actors)
			{
				if (!a.IsInWorld || a.IsDead || a.OccupiesSpace == null || !IsEnemy(a.Owner) || (!Info.FullVision && !a.CanBeViewedByPlayer(player)))
					continue;

				var (x, y) = Square(a.Location);
				now[x, y] += Value(a.Info);
			}

			// Structures out of sight stay on the map as frozen actors: what the player last saw of them still counts.
			if (!Info.FullVision && player.FrozenActorLayer != null)
			{
				foreach (var f in player.FrozenActorLayer.FrozenActorsInRegion(world.Map.AllCells))
				{
					if (!f.IsValid || !f.Visible || !IsEnemy(f.Owner))
						continue;

					var (x, y) = Square(world.Map.CellContaining(f.CenterPosition));
					now[x, y] += Value(f.Info);
				}
			}

			// A square the player sees right now holds only what is in it now: memory (and its fade) is for squares out of sight.
			// Without this, a group walking across squares leaves a trail of copies of itself.
			for (var x = 0; x < cols; x++)
				for (var y = 0; y < rows; y++)
					grid[x, y] = Info.FullVision || SquareVisible(x, y) ? now[x, y] : Math.Max(grid[x, y] * Info.FadePercent / 100f, now[x, y]);

			foreach (var victim in attacks.Keys.ToList())
				if (victim.IsDead || world.WorldTick - attacks[victim].Tick > Info.AttackMemory)
					attacks.Remove(victim);
		}

		/// <summary>One of this player's actors was hit. Being hit also reveals roughly where the attacker stands.</summary>
		public void Attacked(Actor victim, Actor attacker)
		{
			if (IsTraitDisabled || attacker == null || attacker.IsDead || !attacker.IsInWorld || victim.Owner != player || !IsEnemy(attacker.Owner))
				return;

			attacks[victim] = (attacker, world.WorldTick);

			// Some attackers have no place on the map (the firer of a drop pod's shockwave, for one): nothing to mark.
			if (attacker.OccupiesSpace == null)
				return;

			var (x, y) = Square(attacker.Location);
			grid[x, y] = Math.Max(grid[x, y], Value(attacker.Info));
		}

		/// <summary>Remembered enemy value in the grid squares that overlap the given radius around a cell.</summary>
		public int StrengthNear(CPos cell, int radiusCells)
		{
			var (x0, y0) = Square(new CPos(cell.X - radiusCells, cell.Y - radiusCells));
			var (x1, y1) = Square(new CPos(cell.X + radiusCells, cell.Y + radiusCells));
			var sum = 0f;
			for (var x = x0; x <= x1; x++)
				for (var y = y0; y <= y1; y++)
					sum += grid[x, y];

			return (int)sum;
		}

		/// <summary>Attacks on this player's actors within AttackMemory ticks, newest first. Dead victims are left out.</summary>
		public IEnumerable<(Actor Victim, Actor Attacker, int Tick)> RecentAttacks =>
			attacks.Where(kv => !kv.Key.IsDead && kv.Key.IsInWorld && world.WorldTick - kv.Value.Tick <= Info.AttackMemory)
				.OrderByDescending(kv => kv.Value.Tick)
				.Select(kv => (kv.Key, kv.Value.Attacker, kv.Value.Tick));

		public bool FullVision => Info.FullVision;

		// Strength within two squares: a turret's reach (9 cells) spans about that far, so a path keeps out of range, not just off its square.
		float Danger(int x, int y)
		{
			var sum = 0f;
			for (var i = Math.Max(0, x - 2); i <= Math.Min(cols - 1, x + 2); i++)
				for (var j = Math.Max(0, y - 2); j <= Math.Min(rows - 1, y + 2); j++)
					sum += grid[i, j];

			return sum;
		}

		/// <summary>
		/// Waypoints from one cell to another that keep away from remembered enemy strength: an A* over the grid squares, where a step
		/// costs its length times 1 + Danger / StepCostValue. Returns the centre cells of the squares on the way, the last replaced by
		/// the goal, or just the goal when no way is found.
		/// </summary>
		public List<CPos> SafePath(CPos from, CPos to)
		{
			var start = Square(from);
			var goal = Square(to);
			var cost = new float[cols, rows];
			var prev = new (int X, int Y)?[cols, rows];
			for (var x = 0; x < cols; x++)
				for (var y = 0; y < rows; y++)
					cost[x, y] = float.MaxValue;

			float H((int X, int Y) n)
			{
				var dx = Math.Abs(n.X - goal.X);
				var dy = Math.Abs(n.Y - goal.Y);
				return Math.Max(dx, dy) + 0.414f * Math.Min(dx, dy);
			}

			var open = new PriorityQueue<(int X, int Y), float>();
			cost[start.X, start.Y] = 0;
			open.Enqueue(start, H(start));
			while (open.TryDequeue(out var cur, out _))
			{
				if (cur == goal)
					break;

				for (var dx = -1; dx <= 1; dx++)
				{
					for (var dy = -1; dy <= 1; dy++)
					{
						var n = (X: cur.X + dx, Y: cur.Y + dy);
						if ((dx == 0 && dy == 0) || n.X < 0 || n.Y < 0 || n.X >= cols || n.Y >= rows)
							continue;

						var step = (dx != 0 && dy != 0 ? 1.414f : 1f) * (1 + Danger(n.X, n.Y) / Info.StepCostValue);
						var c = cost[cur.X, cur.Y] + step;
						if (c < cost[n.X, n.Y])
						{
							cost[n.X, n.Y] = c;
							prev[n.X, n.Y] = cur;
							open.Enqueue(n, c + H(n));
						}
					}
				}
			}

			var path = new List<CPos>();
			if (start == goal || prev[goal.X, goal.Y] == null)
				return [to];

			for (var at = goal; at != start; at = prev[at.X, at.Y].Value)
				path.Add(new CPos(Math.Min(at.X * Info.CellSize + Info.CellSize / 2, world.Map.MapSize.Width - 1),
					Math.Min(at.Y * Info.CellSize + Info.CellSize / 2, world.Map.MapSize.Height - 1)));

			path.Reverse();
			path[^1] = to;
			return path;
		}

		/// <summary>Remembered strength around a target, less the target's own value: what stands guard over it.</summary>
		public int DefenceNear(CPos cell, int targetValue, int radiusCells)
		{
			return Math.Max(0, StrengthNear(cell, radiusCells) - targetValue);
		}

		/// <summary>The candidate with the most value for the least remembered defence around it, or default when there are none.</summary>
		public T WeakestTarget<T>(IEnumerable<T> candidates, Func<T, CPos> cellOf, Func<T, int> valueOf, int radiusCells)
		{
			return candidates.Select(c => (Item: c, Score: valueOf(c) / (1f + DefenceNear(cellOf(c), valueOf(c), radiusCells))))
				.OrderByDescending(s => s.Score)
				.Select(s => s.Item)
				.FirstOrDefault();
		}
	}

	[Desc("Tells the owner's ThreatMemory when this actor is hit by an enemy.")]
	public class ReportsThreatOnDamageInfo : TraitInfo<ReportsThreatOnDamage> { }

	public class ReportsThreatOnDamage : INotifyDamage
	{
		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			if (e.Damage.Value <= 0 || e.Attacker == null || e.Attacker.IsDead || e.Attacker.Owner == null || self.Owner.IsAlliedWith(e.Attacker.Owner))
				return;

			self.Owner.PlayerActor.TraitOrDefault<ThreatMemory>()?.Attacked(self, e.Attacker);
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using OpenRA.Mods.TGMC.Traits;

	[ScriptPropertyGroup("Threat")]
	public class ThreatMemoryProperties : ScriptPlayerProperties, Requires<ThreatMemoryInfo>
	{
		public ThreatMemoryProperties(ScriptContext context, Player player)
			: base(context, player) { }

		[Desc("Enemy strength this player remembers within radius cells of the cell (the summed cost of what it saw, fading over time).")]
		public int ThreatNear(CPos cell, int radius)
		{
			return Player.PlayerActor.Trait<ThreatMemory>().StrengthNear(cell, radius);
		}
	}
}
