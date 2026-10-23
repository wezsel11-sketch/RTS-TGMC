#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using OpenRA.GameRules;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC
{
	// The lobby settings the mod's own mechanics read. Each has an id, shown in the lobby by TgmcOptionsInfo.
	public static class Options
	{
		public const string FriendlyFire = "tgmc-friendlyfire";
		public const string Infestation = "tgmc-infestation";
		public const string Maturity = "tgmc-maturity";
		public const string TileStep = "tgmc-tilestep";
		public const string BurstTime = "tgmc-bursttime";
		public const string FloatingText = "tgmc-floatingtext";
		public const string Weather = "tgmc-weather";

		/// <summary>A dropdown option's value, or the default when there is no lobby.</summary>
		public static string Value(World world, string id, string defaultValue)
		{
			return world.LobbyInfo == null ? defaultValue : world.LobbyInfo.GlobalSettings.OptionOrDefault(id, defaultValue);
		}

		public static bool Enabled(World world, string id, bool defaultValue)
		{
			// The map's own default (TgmcOptions in its rules) wins over the caller's, so a scenario launched without a lobby
			// screen, whose settings never got the option, still gets what its map asks for.
			var info = world.Map.Rules.Actors[SystemActors.World].TraitInfoOrDefault<Traits.TgmcOptionsInfo>();
			if (info != null)
				defaultValue = id switch
				{
					FriendlyFire => info.FriendlyFireDefault,
					Infestation => info.InfestationDefault,
					Maturity => info.MaturityDefault,
					TileStep => info.TileStepDefault,
					FloatingText => info.FloatingTextDefault,
					_ => defaultValue
				};

			// Scenario and editor worlds have no lobby; use the default there.
			return world.LobbyInfo == null ? defaultValue : world.LobbyInfo.GlobalSettings.OptionOrDefault(id, defaultValue);
		}
	}
}

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.World)]
	[Desc("Adds the mod's mechanics to the lobby as options the host can switch before the match starts.")]
	public class TgmcOptionsInfo : TraitInfo, ILobbyOptions
	{
		[Desc("Default of each lobby option. A map can change these in its rules.")]
		public readonly bool FriendlyFireDefault = true;
		public readonly bool InfestationDefault = true;
		public readonly bool MaturityDefault = true;
		public readonly bool TileStepDefault = false;
		public readonly bool FloatingTextDefault = true;

		[Desc("Weather when there is no lobby, and the lobby's default: clear, rain or dust.")]
		public readonly string WeatherDefault = "clear";

		[GrantedConditionReference]
		public readonly string RainCondition = "rain";

		[GrantedConditionReference]
		public readonly string DustCondition = "dust";

		public override object Create(ActorInitializer init) { return new TgmcOptions(init.Self, this); }

		IEnumerable<LobbyOption> ILobbyOptions.LobbyOptions(MapPreview map)
		{
			yield return new LobbyBooleanOption(map, Options.FriendlyFire,
				"checkbox-tgmc-friendlyfire.label", "checkbox-tgmc-friendlyfire.description", true, 10, FriendlyFireDefault, false);

			yield return new LobbyBooleanOption(map, Options.Infestation,
				"checkbox-tgmc-infestation.label", "checkbox-tgmc-infestation.description", true, 11, InfestationDefault, false);

			yield return new LobbyBooleanOption(map, Options.Maturity,
				"checkbox-tgmc-maturity.label", "checkbox-tgmc-maturity.description", true, 12, MaturityDefault, false);

			yield return new LobbyOption(map, Options.BurstTime,
				"dropdown-tgmc-bursttime.label", "dropdown-tgmc-bursttime.description", true, 14,
				new Dictionary<string, string>
				{
					{ "30", "bursttime-30" }, { "60", "bursttime-60" },
					{ "90", "bursttime-90" }, { "120", "bursttime-120" }
				}, "60", false);

			yield return new LobbyBooleanOption(map, Options.FloatingText,
				"checkbox-tgmc-floatingtext.label", "checkbox-tgmc-floatingtext.description", true, 15, FloatingTextDefault, false);

			yield return new LobbyOption(map, Options.Weather,
				"dropdown-tgmc-weather.label", "dropdown-tgmc-weather.description", true, 16,
				new Dictionary<string, string>
				{
					{ "clear", "weather-clear" }, { "rain", "weather-rain" }, { "dust", "weather-dust" }
				}, WeatherDefault, false);

			yield return new LobbyBooleanOption(map, Options.TileStep,
				"checkbox-tgmc-tilestep.label", "checkbox-tgmc-tilestep.description", true, 13, TileStepDefault, false);
		}
	}

	// Turns the lobby's weather choice into a condition ("rain" or "dust") that the WeatherOverlay traits in world.yaml wait for.
	public class TgmcOptions : INotifyCreated
	{
		readonly Actor self;
		readonly TgmcOptionsInfo info;

		public TgmcOptions(Actor self, TgmcOptionsInfo info)
		{
			this.self = self;
			this.info = info;
		}

		void INotifyCreated.Created(Actor self)
		{
			var weather = Options.Value(self.World, Options.Weather, info.WeatherDefault);
			if (weather == "rain")
				this.self.GrantCondition(info.RainCondition);
			else if (weather == "dust")
				this.self.GrantCondition(info.DustCondition);
		}
	}
}

namespace OpenRA.Mods.TGMC.Warheads
{
	[Desc("Spread damage for explosives. Hurts allies too, unless the lobby's friendly fire option is switched off.")]
	public class ExplosiveDamageWarhead : SpreadDamageWarhead
	{
		public override bool IsValidAgainst(Actor victim, Actor firedBy)
		{
			if (!Options.Enabled(firedBy.World, Options.FriendlyFire, true)
				&& firedBy.Owner.RelationshipWith(victim.Owner) == PlayerRelationship.Ally)
				return false;

			return base.IsValidAgainst(victim, firedBy);
		}
	}
}
