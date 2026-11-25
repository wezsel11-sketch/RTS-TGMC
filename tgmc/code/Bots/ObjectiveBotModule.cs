#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("The Distress Signal for the bot: a group of its own, taken from the units the squad manager has not sent out yet, holds the " +
		"objective. A holder side (Holds) goes for the nearest undecoded terminal and, once its team owns Terminals of them, for the nuke, " +
		"and stays on an armed nuke. The other side contests: it goes for an enemy nuke, else the undecoded terminal an enemy is decoding " +
		"(the furthest along first), else the one with the most enemies at it. It also fortifies: Guards units stand at each undecoded " +
		"terminal, and a Builder unit goes to each so Defenses of Defense can be built beside it. Live only while the lobby's Objective is distress or crash.")]
	public class ObjectiveBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 50;

		[Desc("Unit types the group and the guards are made of.")]
		public readonly string[] Units = [];

		[Desc("Units in the group. It tops up from the squad manager's idle units.")]
		public readonly int Size = 6;

		[Desc("Do not start before this world tick.")]
		public readonly int MinTick = 0;

		[Desc("True for the side that decodes terminals and arms the nuke (marines, SOM); false for the side that stops it (xenos).")]
		public readonly bool Holds = true;

		[ActorReference]
		public readonly string Terminal = "disk-terminal";

		[ActorReference]
		public readonly string Nuke = "nuke";

		public readonly int Terminals = 3;

		[Desc("Cells around an undecoded terminal where enemies count, for the contesting side.")]
		public readonly int ContestRadius = 6;

		[Desc("Units that stand guard at each undecoded terminal, besides the group. 0: none.")]
		public readonly int Guards = 0;

		[Desc("A unit type that gives the build area (the xeno drone): one goes to each undecoded terminal, so Defense can be built there.")]
		public readonly string Builder = null;

		[Desc("The defence built beside each undecoded terminal, and how many.")]
		public readonly string Defense = null;
		public readonly int Defenses = 1;

		[Desc("The production queue that builds the defence.")]
		public readonly string Queue = null;

		[Desc("Cash and resources needed before a new defence is started.")]
		public readonly int MinCash = 400;

		public override object Create(ActorInitializer init) { return new ObjectiveBotModule(init.Self, this); }
	}

	public class ObjectiveBotModule : ConditionalTrait<ObjectiveBotModuleInfo>, IBotTick, IBotNotifyIdleBaseUnits
	{
		readonly World world;
		readonly Player player;
		readonly List<Actor> group = [];
		readonly List<Actor> released = [];

		// Unit to the terminal it guards, and builder to the terminal it stands at.
		readonly Dictionary<Actor, Actor> guards = [];
		readonly Dictionary<Actor, Actor> builders = [];
		bool live;
		Actor target;
		int countdown;

		public ObjectiveBotModule(Actor self, ObjectiveBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		protected override void Created(Actor self)
		{
			base.Created(self);
			var options = world.Map.Rules.Actors[SystemActors.World].TraitInfoOrDefault<TgmcOptionsInfo>();
			var objective = Options.Value(world, Options.Objective, options?.ObjectiveDefault ?? "conquest");
			live = objective == "distress" || objective == "crash";
		}

		public bool IsHolder(Actor a) { return !IsTraitDisabled && (group.Contains(a) || guards.ContainsKey(a) || builders.ContainsKey(a)); }

		void IBotNotifyIdleBaseUnits.UpdatedIdleBaseUnits(List<Actor> idleUnits)
		{
			if (IsTraitDisabled || !live)
				return;

			idleUnits.AddRange(released.Where(a => !a.IsDead && a.IsInWorld));
			released.Clear();
			if (world.WorldTick < Info.MinTick)
				return;

			var free = idleUnits.Where(a => !a.IsDead && a.IsInWorld && a.Owner == player && Info.Units.Contains(a.Info.Name) && !BotUnits.Claimed(a)).ToList();
			if (target != null)
			{
				var take = free.Take(Info.Size - group.Count).ToList();
				group.AddRange(take);
				free.RemoveAll(take.Contains);
				foreach (var a in take)
					idleUnits.Remove(a);
			}

			if (Info.Guards <= 0)
				return;

			foreach (var t in Open())
			{
				for (var n = guards.Values.Count(g => g == t); n < Info.Guards && free.Count > 0; n++)
				{
					var a = free.MinBy(u => (u.Location - t.Location).LengthSquared);
					free.Remove(a);
					idleUnits.Remove(a);
					guards[a] = t;
				}
			}
		}

		IEnumerable<Actor> Live(string type)
		{
			return world.Actors.Where(a => a.Info.Name == type && a.IsInWorld && !a.IsDead);
		}

		// Terminals nobody has decoded yet.
		List<Actor> Open()
		{
			return Live(Info.Terminal).Where(t => t.Owner.NonCombatant).ToList();
		}

		CPos Centre()
		{
			return group.Count > 0 ? new CPos((int)group.Average(a => a.Location.X), (int)group.Average(a => a.Location.Y)) : player.HomeLocation;
		}

		Actor Pick()
		{
			var centre = Centre();
			var nuke = Live(Info.Nuke).FirstOrDefault();
			var open = Open();
			if (Info.Holds)
			{
				if (nuke != null && Live(Info.Terminal).Count(t => t.Owner.IsAlliedWith(player)) >= Info.Terminals)
					return nuke;

				return open.MinByOrDefault(t => (t.Location - centre).LengthSquared);
			}

			if (nuke != null && player.RelationshipWith(nuke.Owner) == PlayerRelationship.Enemy)
				return nuke;

			// The terminal an enemy is decoding, the furthest along first: that is the one about to be lost.
			var decoding = open.Select(t => (t, h: t.TraitOrDefault<HoldObjective>()))
				.Where(x => x.h != null && x.h.Progress > 0 && x.h.Holder != null && player.RelationshipWith(x.h.Holder) == PlayerRelationship.Enemy)
				.OrderByDescending(x => x.h.Progress).Select(x => x.t).FirstOrDefault();
			if (decoding != null)
				return decoding;

			var r = WDist.FromCells(Info.ContestRadius);
			return open.Select(t => (t, n: world.FindActorsInCircle(t.CenterPosition, r).Count(a => player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy
					&& a.Info.HasTraitInfo<IMoveInfo>())))
				.Where(x => x.n > 0).OrderByDescending(x => x.n).Select(x => x.t).FirstOrDefault();
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || !live)
				return;

			// A finished defence is placed at once, before the base builder takes it for its own.
			PlaceDefense(bot);
			if (--countdown > 0)
				return;

			countdown = Info.Interval;
			group.RemoveAll(a => a.IsDead || !a.IsInWorld || a.Owner != player);
			Fortify(bot);
			var next = world.WorldTick < Info.MinTick ? null : Pick();
			if (next == null)
			{
				// Nothing to hold: the group goes back to the squad manager.
				released.AddRange(group);
				group.Clear();
				target = null;
				return;
			}

			var changed = next != target;
			target = next;
			foreach (var a in group)
			{
				// Re-ordered when the target changes, and when a unit stands idle away from it (it chased something, or was blocked).
				if (changed || (a.IsIdle && (a.Location - target.Location).LengthSquared > 4))
					bot.QueueOrder(new Order("AttackMove", a, Target.FromCell(world, target.Location), false));
			}
		}

		void Fortify(IBot bot)
		{
			var open = Open();

			// Guards of a terminal that is gone or decoded go back to the squad manager; builders just stop standing there.
			foreach (var (a, t) in guards.ToList())
			{
				if (a.IsDead || !a.IsInWorld || a.Owner != player || !open.Contains(t))
				{
					guards.Remove(a);
					if (!a.IsDead && a.IsInWorld && a.Owner == player)
						released.Add(a);
				}
				else if (a.IsIdle && (a.Location - t.Location).LengthSquared > 9)
					bot.QueueOrder(new Order("AttackMove", a, Target.FromCell(world, t.Location), false));
			}

			if (Info.Builder == null)
				return;

			foreach (var (a, t) in builders.ToList())
			{
				if (a.IsDead || !a.IsInWorld || a.Owner != player || !open.Contains(t))
					builders.Remove(a);
				else if (a.IsIdle && (a.Location - t.Location).LengthSquared > 4)
					bot.QueueOrder(new Order("Move", a, Target.FromCell(world, t.Location), false));
			}

			foreach (var t in open.Where(t => !builders.ContainsValue(t)))
			{
				var drone = world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.IsIdle && a.Info.Name == Info.Builder && !BotUnits.Claimed(a))
					.MinByOrDefault(a => (a.Location - t.Location).LengthSquared);
				if (drone == null)
					break;

				builders[drone] = t;
				bot.QueueOrder(new Order("Move", drone, Target.FromCell(world, t.Location), false));
			}

			StartDefense(bot, open);
		}

		int DefencesAround(Actor t)
		{
			return world.FindActorsInCircle(t.CenterPosition, WDist.FromCells(5)).Count(a => a.Owner == player && !a.IsDead && a.Info.Name == Info.Defense);
		}

		// A terminal whose builder stands at it and that has fewer than Defenses defences.
		Actor Needy()
		{
			return builders.Where(b => (b.Key.Location - b.Value.Location).LengthSquared <= 4 && DefencesAround(b.Value) < Info.Defenses)
				.Select(b => b.Value).FirstOrDefault();
		}

		ProductionQueue Queue()
		{
			return Info.Defense == null || Info.Queue == null ? null
				: player.PlayerActor.TraitsImplementing<ProductionQueue>().FirstOrDefault(q => q.Info.Type == Info.Queue && q.Enabled);
		}

		void StartDefense(IBot bot, List<Actor> open)
		{
			var queue = Queue();
			if (queue == null || Needy() == null || queue.AllQueued().Any(i => i.Item == Info.Defense) || !queue.CanBuild(world.Map.Rules.Actors[Info.Defense]))
				return;

			var resources = player.PlayerActor.TraitOrDefault<PlayerResources>();
			if (resources == null || resources.GetCashAndResources() < Info.MinCash)
				return;

			bot.QueueOrder(Order.StartProduction(queue.Actor, Info.Defense, 1));
		}

		void PlaceDefense(IBot bot)
		{
			var queue = Queue();
			if (queue == null || !queue.AllQueued().Any(i => i.Done && i.Item == Info.Defense))
				return;

			var needy = Needy();
			if (needy == null)
				return;

			var defence = world.Map.Rules.Actors[Info.Defense];
			var building = defence.TraitInfo<BuildingInfo>();
			// Outside the point's hold circle (2 cells): a defence there would keep the decoders out, and the guards too.
			for (var r = 3; r <= 4; r++)
			{
				for (var dx = -r; dx <= r; dx++)
				{
					for (var dy = -r; dy <= r; dy++)
					{
						if (Math.Max(Math.Abs(dx), Math.Abs(dy)) != r)
							continue;

						var cell = needy.Location + new CVec(dx, dy);
						if (!world.CanPlaceBuilding(cell, defence, building, null) || !building.IsCloseEnoughToBase(world, player, defence, cell))
							continue;

						bot.QueueOrder(new Order("PlaceBuilding", player.PlayerActor, Target.FromCell(world, cell), false)
						{
							TargetString = Info.Defense,
							ExtraData = queue.Actor.ActorID,
							SuppressVisualFeedback = true
						});
						return;
					}
				}
			}
		}
	}
}
