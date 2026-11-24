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
	[Desc("Sends idle attackers to the ore fields no one has claimed yet, to disable them. A field that falls is gone; one a marine has repaired is " +
		"a miner, a normal target. Each idle attacker goes for the nearest unclaimed field.")]
	public class FieldBotModuleInfo : ConditionalTraitInfo
	{
		public readonly int Interval = 120;

		[Desc("The units that go for the fields.")]
		public readonly string[] Attackers = [];

		[Desc("The actor they go for: miner-field for the dormant fields, miner for the marines' miners.")]
		public readonly string Target = "miner-field";

		[Desc("Only targets owned by an enemy player, such as the marines' miners. Off for the dormant fields, which belong to no one.")]
		public readonly bool EnemyOnly = false;

		[Desc("Do not start before this world tick, so the squads get the early game to themselves.")]
		public readonly int MinTick = 0;

		[Desc("The order that sends them. ForceAttack works on a dormant field for engineers (their torch repairs it) and on a miner for xenos.")]
		public readonly string Order = "ForceAttack";

		[Desc("Enemy actors (their base buildings) that make a target too dangerous to go for when one stands within AvoidRadius cells of it: " +
			"an engineer claiming a field beside the hive loses its miner to the first raid.")]
		public readonly string[] AvoidNear = [];

		public readonly int AvoidRadius = 12;

		[Desc("Idle attackers sent per look, 0 for all.")]
		public readonly int Max = 0;

		[Desc("Only while the lobby's Objective is this (\"distress\" for the disk terminals and the nuke); null for always.")]
		public readonly string Objective = null;

		[Desc("Only once the bot owns NeedsOwnedCount actors of this type (the nuke waits for three decoded terminals).")]
		public readonly string NeedsOwned = null;
		public readonly int NeedsOwnedCount = 1;

		public override object Create(ActorInitializer init) { return new FieldBotModule(init.Self, this); }
	}

	public class FieldBotModule : ConditionalTrait<FieldBotModuleInfo>, IBotTick
	{
		readonly World world;
		readonly Player player;
		int countdown;

		public FieldBotModule(Actor self, FieldBotModuleInfo info)
			: base(info)
		{
			world = self.World;
			player = self.Owner;
		}

		void IBotTick.BotTick(IBot bot)
		{
			if (IsTraitDisabled || --countdown > 0 || world.WorldTick < Info.MinTick)
				return;

			countdown = Info.Interval;
			if (Info.Objective != null)
			{
				var options = world.Map.Rules.Actors[SystemActors.World].TraitInfoOrDefault<TgmcOptionsInfo>();
				// Crash is the Distress Signal against the clock: the same points, so the same orders.
				var objective = Options.Value(world, Options.Objective, options?.ObjectiveDefault ?? "conquest");
				if (objective != Info.Objective && !(Info.Objective == "distress" && objective == "crash"))
					return;
			}

			if (Info.NeedsOwned != null && world.Actors.Count(a => a.Owner == player && a.Info.Name == Info.NeedsOwned && !a.IsDead) < Info.NeedsOwnedCount)
				return;

			var taken = new HashSet<Actor>();
			// Dormant fields belong to the Neutral player, which is non-combatant. Miners belong to an enemy player.
			var fields = world.Actors.Where(a => a.Info.Name == Info.Target && a.IsInWorld && !a.IsDead && (Info.EnemyOnly ? player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy : a.Owner.NonCombatant)).ToList();
			if (Info.AvoidNear.Length > 0)
			{
				var danger = world.Actors.Where(a => a.IsInWorld && !a.IsDead && Info.AvoidNear.Contains(a.Info.Name) && player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy).ToList();
				fields.RemoveAll(f => danger.Any(d => (d.Location - f.Location).LengthSquared <= Info.AvoidRadius * Info.AvoidRadius));
			}

			if (fields.Count == 0)
				return;

			// Units another module holds (miner guards, defenders, raiders) stay with it.
			var sent = 0;
			foreach (var attacker in world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.IsIdle && Info.Attackers.Contains(a.Info.Name) && !BotUnits.Claimed(a)))
			{
				if (Info.Max > 0 && sent++ >= Info.Max)
					break;

				var nearest = fields.OrderBy(f => (f.Location - attacker.Location).LengthSquared);
				// Spread the units out: each goes for the nearest target no other unit got this round. With more units than targets they share.
				var field = nearest.FirstOrDefault(f => !taken.Contains(f)) ?? nearest.First();
				taken.Add(field);
				// An attack order on an actor is refused while the enemy cannot be seen; an attack-move to its cell is not.
				bot.QueueOrder(new Order(Info.Order, attacker, Info.Order == "AttackMove" ? Target.FromCell(world, field.Location) : Target.FromActor(field), false));
			}
		}
	}
}
