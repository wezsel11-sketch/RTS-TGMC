#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Mods.Common.Activities;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("An ore field of a converted TGMC map (TGMC's ore drill). It starts broken and dormant: no one owns it and the xenos leave it alone. " +
		"The first marine engineer to repair it claims it and it turns into a miner for that player. Damage can take a field or miner down to " +
		"DisabledPercentage and no further: it is disabled, never destroyed, and a marine repair brings it back.")]
	public class MinerFieldInfo : TraitInfo
	{
		[Desc("Health the field starts with, in percent of its maximum: the broken drill.")]
		public readonly int StartHealthPercentage = 80;

		[Desc("Damage cannot take the field or miner below this percentage of its maximum. Attacks disable it instead of destroying it.")]
		public readonly int DisabledPercentage = 25;

		[ActorReference]
		[Desc("The actor the field becomes once a marine repairs it. Empty on a miner, which only gets the floor.")]
		public readonly string IntoActor = null;

		[GrantedConditionReference]
		[Desc("Granted while the actor is at the floor (disabled). A miner's income is paused by this condition (see CashTrickler in structures.yaml).")]
		public readonly string DisabledCondition = null;

		public override object Create(ActorInitializer init) { return new MinerField(init.Self, this); }
	}

	public class MinerField : INotifyAddedToWorld, INotifyDamage
	{
		readonly MinerFieldInfo info;
		int disabledToken = Actor.InvalidConditionToken;

		public MinerField(Actor self, MinerFieldInfo info)
		{
			this.info = info;
		}

		int Floor(Health health)
		{
			return health.MaxHP * info.DisabledPercentage / 100;
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

			// Only an unclaimed field can be claimed, and only by a marine repair (repairs are negative damage).
			if (info.IntoActor == null || !self.Owner.NonCombatant || e.Damage.Value >= 0 || e.Attacker == null || e.Attacker.Owner.NonCombatant)
				return;

			var owner = e.Attacker.Owner;
			self.ChangeOwner(owner);
			self.QueueActivity(false, new Transform(info.IntoActor)
			{
				ForceHealthPercentage = health.HP * 100 / health.MaxHP,
				Faction = owner.Faction.InternalName
			});
		}
	}
}
