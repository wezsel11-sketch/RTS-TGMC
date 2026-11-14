#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System;
using System.Collections.Immutable;
using System.Linq;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Traits.BotModules.Squads;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("Sends fighters to the bot's outposts (miners, weed nodes, turrets) when they are attacked: enough to beat the attacker as " +
		"ThreatMemory remembers it, not every idle unit, and hands them back once the outpost has been quiet a while. The stock squad " +
		"manager's Protection squad keeps the main base buildings (its ProtectionTypes).")]
	public class DefendBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 25;

		[Desc("Own actor types worth defending.")]
		public readonly string[] Protect = [];

		[Desc("Unit types sent to defend.")]
		public readonly string[] Defenders = [];

		[Desc("Send defenders until their value is this percent of the enemy strength remembered around the outpost.")]
		public readonly int OvermatchPercent = 150;

		[Desc("Cells around the outpost counted, for the enemy and for the fighters already there.")]
		public readonly int Radius = 5;

		[Desc("Ticks without an attack on the outpost before its defenders go home.")]
		public readonly int QuietTicks = 200;

		[Desc("The bot's own actors that mark its base: released defenders walk to the nearest.")]
		public readonly string[] BaseTypes = ["cryo-pod"];

		public override object Create(ActorInitializer init) { return new DefendBotModule(init.Self, this); }
	}

	public class DefendBotModule : ConditionalTrait<DefendBotModuleInfo>, IBotTick, IBotNotifyIdleBaseUnits
	{
		readonly World world;
		readonly Player player;
		readonly Dictionary<Actor, Actor> victimOf = [];
		readonly Dictionary<Actor, int> need = [];
		readonly List<Actor> released = [];
		ThreatMemory memory;
		int countdown;

		public DefendBotModule(Actor self, DefendBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		protected override void Created(Actor self)
		{
			base.Created(self);
			memory = self.TraitOrDefault<ThreatMemory>();
		}

		public bool IsBusy(Actor a) { return !IsTraitDisabled && victimOf.ContainsKey(a); }

		bool Alive(Actor a) { return !a.IsDead && a.IsInWorld && a.Owner == player; }

		bool Near(Actor a, CPos cell) { return (a.Location - cell).LengthSquared <= Info.Radius * Info.Radius; }

		void IBotNotifyIdleBaseUnits.UpdatedIdleBaseUnits(List<Actor> idleUnits)
		{
			if (IsTraitDisabled)
				return;

			idleUnits.AddRange(released.Where(Alive));
			released.Clear();

			foreach (var (victim, wanted) in need.ToList())
			{
				// The outpost may have fallen since the last look: no help for the dead.
				if (!Alive(victim))
				{
					need.Remove(victim);
					continue;
				}

				var left = wanted;
				while (left > 0)
				{
					// Guards never reach this list: their module takes them out of it first.
					var d = idleUnits.Where(a => Alive(a) && Info.Defenders.Contains(a.Info.Name))
						.MinByOrDefault(a => (a.CenterPosition - victim.CenterPosition).LengthSquared);
					if (d == null)
						break;

					idleUnits.Remove(d);
					victimOf[d] = victim;
					left -= System.Math.Max(1, BotUnits.Value(d));
				}

				if (left > 0)
					need[victim] = left;
				else
					need.Remove(victim);
			}
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || memory == null || --countdown > 0)
				return;

			countdown = Info.Interval;
			// An attack counts for an outpost when the outpost itself is hit, or one of the bot's units standing beside it (its guards).
			var outposts = world.Actors.Where(a => Alive(a) && Info.Protect.Contains(a.Info.Name)).ToList();
			var hits = memory.RecentAttacks
				.Select(r => (Victim: Info.Protect.Contains(r.Victim.Info.Name) ? r.Victim
					: outposts.Where(o => Near(r.Victim, o.Location)).MinByOrDefault(o => (o.Location - r.Victim.Location).LengthSquared), r.Attacker, r.Tick))
				.Where(r => r.Victim != null && r.Victim.Owner == player)
				.ToList();
			var attacked = hits.GroupBy(r => r.Victim).Select(g => g.MaxBy(r => r.Tick)).ToList();

			need.Clear();
			foreach (var (victim, _, _) in attacked)
			{
				// Size against the distinct enemies: those in sight around the outpost, plus whoever hit it lately from further off (a rifle
				// reaches 9 cells, beyond Radius). The grid (which may hold a moving group more than once) only when there are none.
				var enemies = world.FindActorsInCircle(victim.CenterPosition, WDist.FromCells(Info.Radius))
					.Where(a => !a.IsDead && player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy && a.CanBeViewedByPlayer(player))
					.Concat(hits.Where(h => h.Victim == victim && !h.Attacker.IsDead && h.Attacker.IsInWorld
						&& player.RelationshipWith(h.Attacker.Owner) == PlayerRelationship.Enemy).Select(h => h.Attacker))
					.Distinct()
					.Sum(BotUnits.Value);
				var threat = (enemies > 0 ? enemies : memory.StrengthNear(victim.Location, Info.Radius)) * Info.OvermatchPercent / 100;
				var there = world.Actors.Where(a => Alive(a) && Info.Defenders.Contains(a.Info.Name) && Near(a, victim.Location))
					.Concat(victimOf.Where(kv => kv.Value == victim && Alive(kv.Key)).Select(kv => kv.Key))
					.Distinct()
					.Sum(BotUnits.Value);
				if (threat > there)
					need[victim] = threat - there;
			}

			foreach (var (d, victim) in victimOf.ToList())
			{
				if (d.IsDead || !d.IsInWorld)
					victimOf.Remove(d);
				else if (!Alive(victim) || !attacked.Any(r => r.Victim == victim && world.WorldTick - r.Tick <= Info.QuietTicks))
				{
					victimOf.Remove(d);
					released.Add(d);
					BotUnits.SendHome(bot, d, Info.BaseTypes);
				}
				else if (d.IsIdle && (d.Location - victim.Location).LengthSquared > 9)
					bot.QueueOrder(new Order("AttackMove", d, Target.FromCell(world, victim.Location), false));
			}
		}
	}
}
