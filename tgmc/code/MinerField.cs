#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using OpenRA.Mods.Common.Activities;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("An ore field of a converted TGMC map (TGMC's ore drill). It starts broken and dormant: no one owns it and the xenos leave it alone. " +
		"Whoever repairs it to full claims it: it turns into a miner for that player (a corrupted miner for the xenos). Damage can take a field " +
		"or miner down to DisabledPercentage and no further: never destroyed. A miner at that floor falls back to a free field: a capture point.")]
	public class MinerFieldInfo : TraitInfo
	{
		[Desc("Health the field starts with, in percent of its maximum: the broken drill.")]
		public readonly int StartHealthPercentage = 80;

		[Desc("Damage cannot take the field or miner below this percentage of its maximum. Attacks disable it instead of destroying it.")]
		public readonly int DisabledPercentage = 25;

		[ActorReference]
		[Desc("The actor the field becomes once a marine repairs it. Empty on a miner, which only gets the floor.")]
		public readonly string IntoActor = null;

		[Desc("On a field: what it becomes for a faction that does not get IntoActor (the xenos' corrupted miner). Faction name, then actor.")]
		public readonly Dictionary<string, string> FactionIntoActors = [];

		[Desc("On a field: a claim counts only once the repair has brought it to this percentage of its health.")]
		public readonly int ClaimPercentage = 100;

		[ActorReference]
		[Desc("On a miner: the free field it falls back to when it is knocked down to the floor. It then belongs to no one until someone claims it.")]
		public readonly string FieldActor = null;

		[GrantedConditionReference]
		[Desc("Granted while the actor is at the floor (disabled). A miner's income is paused by this condition (see CashTrickler in structures.yaml).")]
		public readonly string DisabledCondition = null;

		public override object Create(ActorInitializer init) { return new MinerField(init.Self, this); }
	}

	public class MinerField : INotifyAddedToWorld, INotifyDamage, IDamageModifier
	{
		readonly MinerFieldInfo info;
		readonly Actor self;
		Health health;
		bool changing;
		int disabledToken = Actor.InvalidConditionToken;

		public MinerField(Actor self, MinerFieldInfo info)
		{
			this.info = info;
			this.self = self;
		}

		int Floor(Health health)
		{
			return health.MaxHP * info.DisabledPercentage / 100;
		}

		// Only a lethal hit is cut, to leave 1 HP: the engine refuses the heal-back in Damaged once the actor is dead. A hit that only
		// goes below the floor stays whole, and Damaged lifts the actor back to the floor and lets the point fall. (Cutting every hit
		// to the room above the floor rounded down twice and left a miner stuck 1 HP above it, where every hit did 0.)
		// shortcut: assumes no damage-taken multiplier above 100% on a field or miner (only `agility`, on units, has one).
		int IDamageModifier.GetDamageModifier(Actor attacker, Damage damage)
		{
			health ??= self.Trait<Health>();
			if (damage.Value < health.HP)
				return 100;

			return System.Math.Max(0, (health.HP - 1) * 100 / damage.Value);
		}

		// Keeps the disabled condition in step with the health: granted at the floor, revoked when a repair lifts the actor above it.
		void UpdateDisabled(Actor self, Health health)
		{
			if (info.DisabledCondition == null)
				return;

			var atFloor = health.HP <= Floor(health);
			if (atFloor && disabledToken == Actor.InvalidConditionToken)
				disabledToken = self.GrantCondition(info.DisabledCondition);
			else if (!atFloor && disabledToken != Actor.InvalidConditionToken)
				disabledToken = self.RevokeCondition(disabledToken);
		}

		void INotifyAddedToWorld.AddedToWorld(Actor self)
		{
			// A fresh field starts broken. A field made by a claim is already at its level (Transform gives it a HealthInit),
			// and a miner built by the marines starts whole.
			var health = self.Trait<Health>();
			if (info.IntoActor != null && health.HP == health.MaxHP)
			{
				var missing = health.MaxHP * (100 - info.StartHealthPercentage) / 100;
				if (missing > 0)
					health.InflictDamage(self, self, new Damage(missing), true);
			}

			UpdateDisabled(self, health);
		}

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			var health = self.Trait<Health>();

			// Never destroyed: a hit that would take it below the floor is undone. Our own heal is not a repair, so it stops here.
			if (e.Attacker != self && health.HP < Floor(health))
			{
				health.InflictDamage(self, self, new Damage(-(Floor(health) - health.HP)), true);
				return;
			}

			UpdateDisabled(self, health);
			if (changing)
				return;

			// A held point knocked down to the floor is lost: it is a free field again, for whoever claims it next.
			if (info.FieldActor != null && !self.Owner.NonCombatant && health.HP <= Floor(health))
			{
				changing = true;
				self.ChangeOwner(self.World.WorldActor.Owner);
				self.QueueActivity(false, new Transform(info.FieldActor) { ForceHealthPercentage = info.DisabledPercentage });
				return;
			}

			// Only a free field can be claimed, and only by the repair (negative damage) that brings it to ClaimPercentage:
			// an engineer's torch, or a drone's resin for the xenos.
			if (info.IntoActor == null || !self.Owner.NonCombatant || e.Damage.Value >= 0 || e.Attacker == null || e.Attacker.Owner.NonCombatant
				|| health.HP * 100 < health.MaxHP * info.ClaimPercentage)
				return;

			changing = true;
			var owner = e.Attacker.Owner;
			var into = info.FactionIntoActors.TryGetValue(owner.Faction.InternalName, out var own) ? own : info.IntoActor;
			self.ChangeOwner(owner);
			self.QueueActivity(false, new Transform(into)
			{
				ForceHealthPercentage = 100,
				Faction = owner.Faction.InternalName
			});
		}
	}
}

namespace OpenRA.Mods.TGMC.Traits
{
	using OpenRA.Mods.Common.Traits.Radar;

	[Desc("A capture point on the minimap: a diamond of Radius cells in its holder's colour, or FreeColor while no player holds it.")]
	public class PointRadarSignatureInfo : ConditionalTraitInfo
	{
		public readonly int Radius = 1;
		public readonly Color FreeColor = Color.FromArgb(200, 200, 200);

		public override object Create(ActorInitializer init) { return new PointRadarSignature(this); }
	}

	public class PointRadarSignature : ConditionalTrait<PointRadarSignatureInfo>, IRadarSignature
	{
		public PointRadarSignature(PointRadarSignatureInfo info)
			: base(info) { }

		public void PopulateRadarSignatureCells(Actor self, List<(CPos Cell, Color Color)> destinationBuffer)
		{
			if (IsTraitDisabled)
				return;

			var color = self.Owner.NonCombatant ? Info.FreeColor : self.OwnerColor();
			for (var dx = -Info.Radius; dx <= Info.Radius; dx++)
				for (var dy = -Info.Radius; dy <= Info.Radius; dy++)
					if (System.Math.Abs(dx) + System.Math.Abs(dy) <= Info.Radius && self.World.Map.Contains(self.Location + new CVec(dx, dy)))
						destinationBuffer.Add((self.Location + new CVec(dx, dy), color));
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using System.Linq;
	using OpenRA.Scripting;

	[ScriptPropertyGroup("General")]
	public class ClickOrderProperties : ScriptActorProperties
	{
		public ClickOrderProperties(ScriptContext context, Actor self)
			: base(context, self) { }

		[Desc("Test aid: the order a plain right-click on the actor would give this unit, and its cursor, as \"Order|cursor\"; \"none\" when " +
			"no order takes the target. It asks the unit's order targeters by priority, as the mouse does (UnitOrderGenerator).")]
		public string ClickOrder(Actor target, bool force = false)
		{
			return Ask(Target.FromActor(target), force);
		}

		[Desc("Test aid: the same for a right-click on a ground cell.")]
		public string ClickOrderAt(CPos cell, bool force = false)
		{
			return Ask(Target.FromCell(Self.World, cell), force);
		}

		[Desc("Test aid: give the unit the Move order a right-click on the ground gives (Lua's own Move queues the activity and skips the order).")]
		public void OrderMove(CPos cell)
		{
			Self.World.IssueOrder(new Order("Move", Self, Target.FromCell(Self.World, cell), false));
		}

		[Desc("Test aid: give the unit the forced attack on a ground cell that a Ctrl-click gives.")]
		public void ForceAttackCell(CPos cell)
		{
			Self.World.IssueOrder(new Order("ForceAttack", Self, Target.FromCell(Self.World, cell), false));
		}

		string Ask(Target t, bool force)
		{
			var targeters = Self.TraitsImplementing<IIssueOrder>()
				.SelectMany(trait => trait.Orders)
				.OrderByDescending(o => o.OrderPriority);

			foreach (var o in targeters)
			{
				var modifiers = force ? TargetModifiers.ForceAttack : TargetModifiers.None;
				string cursor = null;
				if (o.CanTarget(Self, t, ref modifiers, ref cursor))
					return o.OrderID + "|" + cursor;
			}

			return "none";
		}
	}

	[ScriptPropertyGroup("Production")]
	public class BuildListProperties : ScriptPlayerProperties
	{
		public BuildListProperties(ScriptContext context, Player player)
			: base(context, player) { }

		[Desc("Test aid: the names the player can build now in the queues of this type (for example \"Infantry\"), sorted, joined by commas.")]
		public string BuildList(string queueType)
		{
			return string.Join(",", Player.PlayerActor.TraitsImplementing<OpenRA.Mods.Common.Traits.ProductionQueue>()
				.Where(q => q.Info.Type == queueType && q.Enabled)
				.SelectMany(q => q.BuildableItems())
				.Select(a => a.Name).Distinct().OrderBy(n => n));
		}
	}
}
