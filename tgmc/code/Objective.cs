#region Copyright & License Information
/*
 * TGMC mod for OpenRA. Personal, non-commercial.
 */
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("A point of TGMC's Distress Signal objective, live only when the lobby's Objective is \"distress\". A side of one of Factions " +
		"holds it by keeping a unit of HolderTypes within Radius, with no enemy unit there, for HoldTicks. A disk terminal (Countdown 0) " +
		"then belongs to that side. The nuke (Countdown above 0) can only be held by a side that owns Terminals of the Terminal actors; " +
		"held, it is armed and goes off after Countdown ticks, which pause while enemies stand at it and none of the owner's. " +
		"It kills every enemy actor on the map.")]
	public class HoldObjectiveInfo : TraitInfo
	{
		public readonly WDist Radius = WDist.FromCells(2);

		public readonly int HoldTicks = 500;

		public readonly HashSet<string> Factions = ["marines", "som"];

		public readonly BitSet<TargetableType> HolderTypes = new("Human");

		[ActorReference]
		public readonly string Terminal = null;

		public readonly int Terminals = 0;

		public readonly int Countdown = 0;

		[GrantedConditionReference]
		[Desc("Granted once the point is taken: a decoded terminal, an armed nuke.")]
		public readonly string ArmedCondition = "armed";

		[Desc("A weapon fired at the point when the nuke goes off (the blast and its shake).")]
		public readonly string DetonateWeapon = null;

		public readonly string[] DoneSounds = [];

		[Desc("Fluent keys of the lines both sides read when the point is taken and (for the nuke) when it goes off.")]
		public readonly string DoneNotification = null;
		public readonly string DetonateNotification = null;

		public readonly Color HoldColor = Color.FromArgb(255, 220, 60);
		public readonly Color ArmedColor = Color.FromArgb(255, 70, 50);

		public override object Create(ActorInitializer init) { return new HoldObjective(init.Self, this); }
	}

	public class HoldObjective : ITick, ISelectionBar, INotifyCreated
	{
		readonly HoldObjectiveInfo info;
		bool live;
		Player holder;
		int progress;
		int timer = -1;

		public bool Taken { get; private set; }
		public bool Armed => timer >= 0;

		public HoldObjective(Actor self, HoldObjectiveInfo info) { this.info = info; }

		void INotifyCreated.Created(Actor self)
		{
			var options = self.World.Map.Rules.Actors[SystemActors.World].TraitInfoOrDefault<TgmcOptionsInfo>();
			var objective = Options.Value(self.World, Options.Objective, options?.ObjectiveDefault ?? "conquest");
			live = objective == "distress" || objective == "crash";
		}

		bool Holds(Actor a, Player p)
		{
			return a.Owner == p && a.GetEnabledTargetTypes().Overlaps(info.HolderTypes);
		}

		void ITick.Tick(Actor self)
		{
			if (!live || Taken)
				return;

			var near = self.World.FindActorsInCircle(self.CenterPosition, info.Radius)
				.Where(a => a != self && a.IsInWorld && !a.IsDead && !a.Owner.NonCombatant && a.Info.HasTraitInfo<IMoveInfo>()).ToList();

			if (Armed)
			{
				var owner = self.Owner;
				var contested = near.Any(a => owner.RelationshipWith(a.Owner) == PlayerRelationship.Enemy) && !near.Any(a => Holds(a, owner));
				if (!contested && --timer <= 0)
					Detonate(self);

				return;
			}

			// One team in the circle, with no enemy of it there: the first of its players holds (marines and SOM allied in a team
			// game hold together). Anything else lets the progress run down.
			var sides = near.Where(a => info.Factions.Contains(a.Owner.Faction.InternalName) && a.GetEnabledTargetTypes().Overlaps(info.HolderTypes))
				.Select(a => a.Owner).Distinct().ToList();
			var side = sides.Count > 0 && sides.All(p => p.IsAlliedWith(sides[0]))
				&& !near.Any(a => sides[0].RelationshipWith(a.Owner) == PlayerRelationship.Enemy) ? sides[0] : null;
			if (side != null && info.Terminals > 0
				&& self.World.Actors.Count(a => a.Info.Name == info.Terminal && !a.IsDead && a.Owner.IsAlliedWith(side)) < info.Terminals)
				side = null;

			if (side == null || (holder != null && !side.IsAlliedWith(holder)))
			{
				progress = System.Math.Max(0, progress - 2);
				if (progress == 0)
					holder = side;

				return;
			}

			holder ??= side;
			if (++progress < info.HoldTicks)
				return;

			self.ChangeOwnerSync(holder);
			Fx.Sound(self.World, self.CenterPosition, info.DoneSounds);
			if (info.DoneNotification != null)
				foreach (var p in self.World.Players.Where(p => p.Playable))
					TextNotificationsManager.AddTransientLine(p, info.DoneNotification);

			self.GrantCondition(info.ArmedCondition);
			if (info.Countdown > 0)
				timer = info.Countdown;
			else
				Taken = true;
		}

		void Detonate(Actor self)
		{
			Taken = true;
			timer = -1;
			var owner = self.Owner;
			if (info.DetonateWeapon != null)
				self.World.Map.Rules.Weapons[info.DetonateWeapon.ToLowerInvariant()].Impact(Target.FromPos(self.CenterPosition), self);

			if (info.DetonateNotification != null)
				foreach (var p in self.World.Players.Where(p => p.Playable))
					TextNotificationsManager.AddTransientLine(p, info.DetonateNotification);

			// The planet goes with it: every enemy actor dies, and the conquest rules end the match.
			var doomed = self.World.Actors.Where(a => a.IsInWorld && !a.IsDead && !a.Owner.NonCombatant
				&& owner.RelationshipWith(a.Owner) == PlayerRelationship.Enemy && a.Info.HasTraitInfo<IHealthInfo>()).ToList();
			foreach (var a in doomed)
				a.Kill(self);
		}

		float ISelectionBar.GetValue()
		{
			if (Armed)
				return timer / (float)info.Countdown;

			return live && !Taken ? progress / (float)info.HoldTicks : 0;
		}

		Color ISelectionBar.GetColor() { return Armed ? info.ArmedColor : info.HoldColor; }

		bool ISelectionBar.DisplayWhenEmpty => false;
	}

	[TraitLocation(SystemActors.World)]
	[Desc("TGMC's Crash mode (the lobby's Objective \"crash\"): the Distress Signal points, against the clock. If no nuke has gone off " +
		"when TimeLimit runs out, the hive has the colony: every actor of Factions dies and the conquest rules end the match.")]
	public class CrashTimerInfo : TraitInfo
	{
		public readonly int TimeLimit = 37500;

		public readonly HashSet<string> Factions = ["marines", "som"];

		[Desc("Fluent keys of the warnings, given this many ticks before the end.")]
		public readonly Dictionary<int, string> Warnings = new() { { 7500, "notification-crash-5min" }, { 1500, "notification-crash-1min" } };

		public readonly string LostNotification = "notification-crash-lost";

		public override object Create(ActorInitializer init) { return new CrashTimer(this); }
	}

	public class CrashTimer : ITick, INotifyCreated
	{
		readonly CrashTimerInfo info;
		bool live;

		public CrashTimer(CrashTimerInfo info) { this.info = info; }

		void INotifyCreated.Created(Actor self)
		{
			var options = self.World.Map.Rules.Actors[SystemActors.World].TraitInfoOrDefault<TgmcOptionsInfo>();
			live = Options.Value(self.World, Options.Objective, options?.ObjectiveDefault ?? "conquest") == "crash";
		}

		void ITick.Tick(Actor self)
		{
			if (!live)
				return;

			var left = info.TimeLimit - self.World.WorldTick;
			if (info.Warnings.TryGetValue(left, out var warning))
				foreach (var p in self.World.Players.Where(p => p.Playable))
					TextNotificationsManager.AddTransientLine(p, warning);

			if (left > 0)
				return;

			live = false;
			// A nuke that already went off has ended the match; one still counting down loses the race.
			foreach (var p in self.World.Players.Where(p => p.Playable))
				TextNotificationsManager.AddTransientLine(p, info.LostNotification);

			var doomed = self.World.Actors.Where(a => a.IsInWorld && !a.IsDead && info.Factions.Contains(a.Owner.Faction.InternalName)
				&& !a.Owner.NonCombatant && a.Info.HasTraitInfo<IHealthInfo>()).ToList();
			foreach (var a in doomed)
				a.Kill(self);
		}
	}
}
