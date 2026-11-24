using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Cries out when hurt, with phrases of its voice set: PainVoice on a hit, at most once per Cooldown ticks, and MedicVoice " +
		"when a hit takes it to heavy damage with no healer of its own side within HealerRange. A phrase the voice set lacks is skipped.")]
	public class CriesInPainInfo : TraitInfo
	{
		public readonly string PainVoice = "Pain";
		public readonly string MedicVoice = "Medic";

		[Desc("Percent chance that a hit draws a cry.")]
		public readonly int Chance = 45;

		[Desc("Ticks between two cries of one unit.")]
		public readonly int Cooldown = 60;

		[Desc("Actor names that count as a healer.")]
		public readonly HashSet<string> Healers = [];

		public readonly WDist HealerRange = WDist.FromCells(6);

		public override object Create(ActorInitializer init) { return new CriesInPain(this); }
	}

	public class CriesInPain : INotifyDamage
	{
		readonly CriesInPainInfo info;
		int next;

		public CriesInPain(CriesInPainInfo info) { this.info = info; }

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			// Sound only: nothing here touches the synced game state, so the local random is safe.
			if (e.Damage.Value <= 0 || self.IsDead || self.World.WorldTick < next)
				return;

			var phrase = info.PainVoice;
			if (e.DamageState >= DamageState.Heavy && e.PreviousDamageState < DamageState.Heavy
				&& !self.World.FindActorsInCircle(self.CenterPosition, info.HealerRange)
					.Any(a => a != self && a.Owner == self.Owner && info.Healers.Contains(a.Info.Name)))
				phrase = info.MedicVoice;
			else if (Game.CosmeticRandom.Next(100) >= info.Chance)
				return;

			if (!self.HasVoice(phrase))
				return;

			next = self.World.WorldTick + info.Cooldown;
			self.PlayVoiceLocal(phrase, 1f);
		}
	}
	[Desc("Voiced, with a rest between shouts: a phrase named in Throttled is refused while the last one of this client is under " +
		"ThrottleTicks old, so a group sent to attack again and again does not shout each time. Local and cosmetic.")]
	public class TgmcVoicedInfo : VoicedInfo
	{
		public readonly HashSet<string> Throttled = ["Attack"];
		public readonly int ThrottleTicks = 100;

		public override object Create(ActorInitializer init) { return new TgmcVoiced(this); }
	}

	public class TgmcVoiced : Voiced, IVoiced
	{
		// Sound only, never read by the game state. One value for the client: the last throttled shout, as a world and its tick.
		static World lastWorld;
		static int lastTick;
		readonly TgmcVoicedInfo info;

		public TgmcVoiced(TgmcVoicedInfo info)
			: base(info) { this.info = info; }

		bool IVoiced.PlayVoice(Actor self, string phrase, string variant)
		{
			if (IsTraitDisabled || phrase == null || string.IsNullOrEmpty(Info.VoiceSet))
				return false;

			if (info.Throttled.Contains(phrase))
			{
				// Refused quietly: the caller treats it as played, so no other unit of the group shouts in its place.
				if (lastWorld == self.World && self.World.WorldTick - lastTick < info.ThrottleTicks)
					return true;

				lastWorld = self.World;
				lastTick = self.World.WorldTick;
			}

			return Game.Sound.PlayPredefined(SoundType.World, self.World.Map.Rules, null, self, Info.VoiceSet.ToLowerInvariant(), phrase, variant, true, WPos.Zero, Info.Volume, true);
		}
	}
}
