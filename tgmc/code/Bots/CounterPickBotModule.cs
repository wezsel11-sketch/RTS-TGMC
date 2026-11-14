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
	[Desc("One counter: when the enemy fields many of Enemies, the AI wants more of Units.")]
	public class CounterRule
	{
		[Desc("Enemy unit types this rule reacts to.")]
		public readonly string[] Enemies = [];

		[Desc("Own unit types that counter them.")]
		public readonly string[] Units = [];

		[Desc("How much the want for these units grows when every enemy seen is of the Enemies types (scaled down by their share).")]
		public readonly int Bonus = 100;

		public CounterRule(MiniYaml yaml) { FieldLoader.Load(this, yaml); }
	}

	[TraitLocation(SystemActors.Player)]
	[Desc("Looks at what the enemy has been seen to field and asks the unit builder for units that counter it.")]
	public class CounterPickBotModuleInfo : ConditionalTraitInfo
	{
		[Desc("Ticks between looks at the enemy.")]
		public readonly int Interval = 150;

		[Desc("Does nothing while cash is below this.")]
		public readonly int MinCash = 150;

		[Desc("Enemy units that must have been seen before the AI reacts.")]
		public readonly int MinSeen = 4;

		[Desc("Open requests for one unit type before it stops asking for more.")]
		public readonly int MaxPending = 2;

		[Desc("Most units of one type the AI keeps through counter-picking.")]
		public readonly int MaxOwned = 8;

		[Desc("How much of what was seen is remembered each look (percent), so an old sighting fades.")]
		public readonly int MemoryPercent = 96;

		[FieldLoader.LoadUsing(nameof(LoadCounters))]
		public readonly ImmutableArray<CounterRule> Counters = [];

		static object LoadCounters(MiniYaml yaml)
		{
			var counters = yaml.NodeWithKeyOrDefault("Counters");
			return counters == null ? [] : counters.Value.Nodes.Select(n => new CounterRule(n.Value)).ToImmutableArray();
		}

		public override object Create(ActorInitializer init) { return new CounterPickBotModule(init.Self, this); }
	}

	public class CounterPickBotModule : ConditionalTrait<CounterPickBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		readonly Dictionary<string, float> seen = [];
		int countdown;

		public CounterPickBotModule(Actor self, CounterPickBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0)
				return;

			countdown = Info.Interval;

			foreach (var key in seen.Keys.ToList())
				seen[key] = seen[key] * Info.MemoryPercent / 100f;

			var now = new Dictionary<string, int>();
			foreach (var a in world.Actors)
			{
				if (a.IsDead || !a.IsInWorld || a.Owner == player || player.RelationshipWith(a.Owner) != PlayerRelationship.Enemy || !a.CanBeViewedByPlayer(player))
					continue;

				now[a.Info.Name] = now.GetValueOrDefault(a.Info.Name) + 1;
			}

			foreach (var (name, count) in now)
				seen[name] = System.Math.Max(seen.GetValueOrDefault(name), count);

			var total = seen.Values.Sum();
			if (total < Info.MinSeen || player.PlayerActor.Trait<PlayerResources>().GetCashAndResources() < Info.MinCash)
				return;

			var buildable = AIUtils.FindQueuesByCategory(player).SelectMany(g => g).SelectMany(q => q.BuildableItems()).Select(i => i.Name).ToHashSet();
			var mine = world.Actors.Where(a => a.Owner == player && !a.IsDead && a.IsInWorld).GroupBy(a => a.Info.Name).ToDictionary(g => g.Key, g => g.Count());
			var requesters = player.PlayerActor.TraitsImplementing<IBotRequestUnitProduction>().ToArray();

			var score = new Dictionary<string, float>();
			foreach (var rule in Info.Counters)
			{
				var share = rule.Enemies.Sum(e => seen.GetValueOrDefault(e)) / total;
				if (share <= 0)
					continue;

				foreach (var unit in rule.Units)
					score[unit] = score.GetValueOrDefault(unit) + rule.Bonus * share;
			}

			var best = score.Where(kv => buildable.Contains(kv.Key) && mine.GetValueOrDefault(kv.Key) < Info.MaxOwned
					&& requesters.Sum(r => r.RequestedProductionCount(bot, kv.Key)) < Info.MaxPending)
				.OrderByDescending(kv => kv.Value).Select(kv => kv.Key).FirstOrDefault();

			if (best != null)
				foreach (var r in requesters)
					r.RequestUnitProduction(bot, best);
		}
	}
}
