#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("The Distress Signal for the bot: a group of its own, taken from the units the squad manager has not sent out yet, holds the " +
		"objective. A holder side (Holds) goes for the nearest undecoded terminal and, once its team owns Terminals of them, for the nuke, " +
		"and stays on an armed nuke. The other side contests: it goes for an enemy nuke, else the undecoded terminal with the most enemies " +
		"at it. Live only while the lobby's Objective is distress or crash.")]
	public class ObjectiveBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 50;

		[Desc("Unit types the group is made of.")]
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

		public override object Create(ActorInitializer init) { return new ObjectiveBotModule(init.Self, this); }
	}

	public class ObjectiveBotModule : ConditionalTrait<ObjectiveBotModuleInfo>, IBotTick, IBotNotifyIdleBaseUnits
	{
		readonly World world;
		readonly Player player;
		readonly List<Actor> group = [];
		readonly List<Actor> released = [];
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

		public bool IsHolder(Actor a) { return !IsTraitDisabled && group.Contains(a); }

		void IBotNotifyIdleBaseUnits.UpdatedIdleBaseUnits(List<Actor> idleUnits)
		{
			if (IsTraitDisabled || !live)
				return;

			idleUnits.AddRange(released.Where(a => !a.IsDead && a.IsInWorld));
			released.Clear();
			if (target == null || world.WorldTick < Info.MinTick)
				return;

			var free = idleUnits.Where(a => !a.IsDead && a.IsInWorld && a.Owner == player && Info.Units.Contains(a.Info.Name) && !BotUnits.Claimed(a))
				.Take(Info.Size - group.Count).ToList();
			foreach (var a in free)
				idleUnits.Remove(a);

			group.AddRange(free);
		}

		IEnumerable<Actor> Live(string type)
		{
			return world.Actors.Where(a => a.Info.Name == type && a.IsInWorld && !a.IsDead);
		}

		CPos Centre()
		{
			return group.Count > 0 ? new CPos((int)group.Average(a => a.Location.X), (int)group.Average(a => a.Location.Y)) : player.HomeLocation;
		}

		Actor Pick()
		{
			var centre = Centre();
			var nuke = Live(Info.Nuke).FirstOrDefault();
			var open = Live(Info.Terminal).Where(t => t.Owner.NonCombatant).ToList();
			if (Info.Holds)
			{
				if (nuke != null && Live(Info.Terminal).Count(t => t.Owner.IsAlliedWith(player)) >= Info.Terminals)
					return nuke;

				return open.MinByOrDefault(t => (t.Location - centre).LengthSquared);
			}

			if (nuke != null && player.RelationshipWith(nuke.Owner) == PlayerRelationship.Enemy)
				return nuke;

			var r = WDist.FromCells(Info.ContestRadius);
			return open.Select(t => (t, n: world.FindActorsInCircle(t.CenterPosition, r).Count(a => player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy
					&& a.Info.HasTraitInfo<IMoveInfo>())))
				.Where(x => x.n > 0).OrderByDescending(x => x.n).Select(x => x.t).FirstOrDefault();
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || !live || --countdown > 0)
				return;

			countdown = Info.Interval;
			group.RemoveAll(a => a.IsDead || !a.IsInWorld || a.Owner != player);
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
	}
}
