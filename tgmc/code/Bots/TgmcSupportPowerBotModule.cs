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
	[Desc("Fires the bot's support powers by the same Decisions as the stock SupportPowerBotModule, but judges the spot around each actor it " +
		"can see (and each frozen one) instead of on a fixed grid of squares, where a group standing across a square's edge counted in none of them.")]
	public class TgmcSupportPowerBotModuleInfo : SupportPowerBotModuleInfo
	{
		[Desc("Ticks between looks while a power is ready but nothing is worth it. Used instead of each decision's Minimum/MaximumScanTimeInterval: " +
			"this scan is cheap, and a group seen for a moment (a scout about to die) should not be missed for ten seconds.")]
		public readonly int ScanInterval = 50;

		// The field loader looks for the base's private loader on this type, so it is repeated here.
		static object LoadDecisions(MiniYaml yaml)
		{
			var decisions = yaml.NodeWithKeyOrDefault("Decisions");
			return decisions == null ? ImmutableArray<SupportPowerDecision>.Empty : decisions.Value.Nodes.Select(d => new SupportPowerDecision(d.Value)).ToImmutableArray();
		}

		public override object Create(ActorInitializer init) { return new TgmcSupportPowerBotModule(init.Self, this); }
	}

	public class TgmcSupportPowerBotModule : ConditionalTrait<TgmcSupportPowerBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		readonly Dictionary<SupportPowerInstance, int> waiting = [];
		readonly Dictionary<string, SupportPowerDecision> decisions = [];
		SupportPowerManager manager;

		public TgmcSupportPowerBotModule(Actor self, TgmcSupportPowerBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
			foreach (var d in info.Decisions)
				decisions[d.OrderName] = d;
		}

		protected override void Created(Actor self)
		{
			manager = self.Owner.PlayerActor.Trait<SupportPowerManager>();
			base.Created(self);
		}

		void IBotTick.BotTick(IBot bot)
		{
			foreach (var sp in manager.Powers.Values)
			{
				if (sp.Disabled || !decisions.TryGetValue(sp.Info.OrderName, out var decision))
					continue;

				waiting.TryAdd(sp, 0);
				if (waiting[sp] > 0)
				{
					waiting[sp]--;
					continue;
				}

				if (!sp.Ready)
					continue;

				var spot = BestSpot(decision);
				if (spot == null)
				{
					// Nothing worth it now: look again soon.
					waiting[sp] = Info.ScanInterval;
					continue;
				}

				// A few ticks for the order to land before looking again.
				waiting[sp] = 10;
				bot.QueueOrder(new Order(sp.Key, manager.Self, Target.FromCell(world, spot.Value), false) { SuppressVisualFeedback = true, ExtraData = uint.MaxValue });
			}
		}

		// Where the decision scores highest, if that reaches its MinimumAttractiveness. First what each seen actor's cell offers (the
		// considerations that count for a spot only), then the full judgement on a small grid around the best of them, so a strike can
		// shift off a group that stands next to our own troops, as the stock module's fine scan does.
		CPos? BestSpot(SupportPowerDecision decision)
		{
			var map = world.Map;
			var gains = decision.Considerations.Where(c => c.Attractiveness > 0).ToList();
			var wanted = gains.Select(c => c.Against).ToHashSet();
			var cells = world.Actors
				.Where(a => a.IsInWorld && !a.IsDead && a.OccupiesSpace != null && wanted.Contains(player.RelationshipWith(a.Owner)) && a.CanBeViewedByPlayer(player))
				.Select(a => a.CenterPosition)
				.Concat(player.FrozenActorLayer?.FrozenActorsInRegion(map.AllCells)
					.Where(f => f.IsValid && wanted.Contains(player.RelationshipWith(f.Owner)))
					.Select(f => f.CenterPosition) ?? [])
				.Select(map.CellContaining)
				.Distinct();

			var seeds = cells.Select(c => (Cell: c, Gain: Score(gains, map.CenterOfCell(c))))
				.Where(s => s.Gain >= decision.MinimumAttractiveness)
				.OrderByDescending(s => s.Gain)
				.Take(8);

			CPos? best = null;
			var bestScore = decision.MinimumAttractiveness - 1;
			var tried = new HashSet<CPos>();
			foreach (var seed in seeds)
			{
				for (var dx = -4; dx <= 4; dx += 2)
				{
					for (var dy = -4; dy <= 4; dy += 2)
					{
						var cell = seed.Cell + new CVec(dx, dy);
						if (!map.Contains(cell) || !tried.Add(cell))
							continue;

						var score = decision.GetAttractiveness(map.CenterOfCell(cell), player);
						if (score > bestScore)
						{
							bestScore = score;
							best = cell;
						}
					}
				}
			}

			return best;
		}

		// SupportPowerDecision.GetAttractiveness for some of its considerations only.
		int Score(List<SupportPowerDecision.Consideration> considerations, WPos pos)
		{
			var score = 0;
			foreach (var c in considerations)
			{
				foreach (var a in world.FindActorsInCircle(pos, c.CheckRadius))
					score += c.GetAttractiveness(a, player.RelationshipWith(a.Owner), player);

				var delta = new WVec(c.CheckRadius, c.CheckRadius, WDist.Zero);
				var region = new CellRegion(world.Map.Grid.Type, world.Map.CellContaining(pos - delta), world.Map.CellContaining(pos + delta));
				foreach (var f in player.FrozenActorLayer?.FrozenActorsInRegion(region) ?? [])
					if (f.IsValid)
						score += c.GetAttractiveness(f, player.RelationshipWith(f.Owner));
			}

			return score;
		}
	}
}
