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

			for (var x = 0; x < cols; x++)
				for (var y = 0; y < rows; y++)
					grid[x, y] = Math.Max(grid[x, y] * Info.FadePercent / 100f, now[x, y]);

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

		/// <summary>The candidate with the most value for the least remembered defence around it, or default when there are none.</summary>
		public T WeakestTarget<T>(IEnumerable<T> candidates, Func<T, CPos> cellOf, Func<T, int> valueOf, int radiusCells)
		{
			return candidates.Select(c => (Item: c, Score: valueOf(c) / (1f + StrengthNear(cellOf(c), radiusCells))))
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
