using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Scripting;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Posts an under-attack event and a radar ping when an enemy damages this unit, at most once per CooldownTicks for its owner.")]
	public class AlertOnDamageInfo : TraitInfo
	{
		public readonly int CooldownTicks = 250;

		[Desc("Fluent key of the event posted. Each key has its own cooldown, so a raid on a miner still warns during a fight at the base.")]
		public readonly string Event = "event-under-attack";

		[Desc("Colour of the radar ping.")]
		public readonly Color PingColor = Color.FromArgb(255, 160, 60);

		public override object Create(ActorInitializer init) { return new AlertOnDamage(this); }
	}

	public class AlertOnDamage : INotifyDamage
	{
		readonly AlertOnDamageInfo info;

		public AlertOnDamage(AlertOnDamageInfo info) { this.info = info; }

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			if (e.Damage.Value <= 0 || e.Attacker == null || e.Attacker.IsDead || self.Owner.IsAlliedWith(e.Attacker.Owner))
				return;

			if (!TgmcEventLog.PostLimited(self.World, self.Owner, info.Event, self.CenterPosition, info.CooldownTicks))
				return;

			self.World.WorldActor.TraitOrDefault<RadarPings>()?.Add(
				() => self.Owner.IsAlliedWith(self.World.RenderPlayer), self.CenterPosition, info.PingColor, 60);
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using OpenRA.Mods.TGMC.Traits;

	[ScriptPropertyGroup("Combat")]
	public class TgmcEventCountProperties : ScriptPlayerProperties
	{
		public TgmcEventCountProperties(ScriptContext context, Player player)
			: base(context, player) { }

		[Desc("How many times the event with this fluent key has been posted for the player this match.")]
		public int EventCount(string key)
		{
			var log = Player.World.WorldActor.TraitOrDefault<TgmcEventLog>();
			return log == null ? 0 : log.Count(Player, key);
		}
	}
}
