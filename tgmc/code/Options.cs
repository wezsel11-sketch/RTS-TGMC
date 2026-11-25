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
		public const string Formation = "tgmc-formation";
		public const string BurstTime = "tgmc-bursttime";
		public const string FloatingText = "tgmc-floatingtext";
		public const string Weather = "tgmc-weather";
		public const string Night = "tgmc-night";
		public const string LandingIntro = "tgmc-landingintro";
		public const string Downed = "tgmc-downed";
		public const string Objective = "tgmc-objective";
		public const string LandingDelay = "tgmc-landingdelay";

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
					Formation => info.FormationDefault,
					FloatingText => info.FloatingTextDefault,
					Night => info.NightDefault,
					LandingIntro => info.LandingIntroDefault,
					Downed => info.DownedDefault,
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
		public readonly bool FormationDefault = true;
		public readonly bool FloatingTextDefault = true;
		public readonly bool NightDefault = false;

		[Desc("Marines and SOM arrive by dropship at the start: the Alamo lands, the squad walks out, the ship leaves.")]
		public readonly bool LandingIntroDefault = true;

		[Desc("Marines fall and bleed out instead of dying at once: a corpsman revives them, a xeno cocoons them (Downable in Downed.cs).")]
		public readonly bool DownedDefault = true;

		[Desc("How a match is won: \"conquest\" (destroy everything) or \"distress\" (TGMC's disks and nuke, HoldObjective in Objective.cs, as well as conquest).")]
		public readonly string ObjectiveDefault = "conquest";

		[Desc("Seconds the marines and SOM are held at their landing zone at the start, as TGMC's fog walls keep them out while the hive sets up: 0, 60, 120 or 180.")]
		public readonly string LandingDelayDefault = "0";

		[Desc("Weather when there is no lobby, and the lobby's default: clear, rain, dust, ash, snow or acidrain.")]
		public readonly string WeatherDefault = "clear";

		[GrantedConditionReference]
		public readonly string RainCondition = "rain";

		[GrantedConditionReference]
		public readonly string DustCondition = "dust";

		[GrantedConditionReference]
		public readonly string AshCondition = "ash";

		[GrantedConditionReference]
		public readonly string SnowCondition = "snow";

		[GrantedConditionReference]
		public readonly string AcidRainCondition = "acidrain";

		public override object Create(ActorInitializer init) { return new TgmcOptions(init.Self, this); }

		// Display orders are negative so the mod's own options lead the lobby's list (the engine's sit at 0).
		IEnumerable<LobbyOption> ILobbyOptions.LobbyOptions(MapPreview map)
		{
			yield return new LobbyBooleanOption(map, Options.FriendlyFire,
				"checkbox-tgmc-friendlyfire.label", "checkbox-tgmc-friendlyfire.description", true, -18, FriendlyFireDefault, false);

			yield return new LobbyBooleanOption(map, Options.Infestation,
				"checkbox-tgmc-infestation.label", "checkbox-tgmc-infestation.description", true, -17, InfestationDefault, false);

			yield return new LobbyBooleanOption(map, Options.Maturity,
				"checkbox-tgmc-maturity.label", "checkbox-tgmc-maturity.description", true, -16, MaturityDefault, false);

			yield return new LobbyOption(map, Options.BurstTime,
				"dropdown-tgmc-bursttime.label", "dropdown-tgmc-bursttime.description", true, -19,
				new Dictionary<string, string>
				{
					{ "30", "bursttime-30" }, { "60", "bursttime-60" },
					{ "90", "bursttime-90" }, { "120", "bursttime-120" }
				}, "60", false);

			yield return new LobbyBooleanOption(map, Options.FloatingText,
				"checkbox-tgmc-floatingtext.label", "checkbox-tgmc-floatingtext.description", true, -14, FloatingTextDefault, false);

			yield return new LobbyOption(map, Options.Weather,
				"dropdown-tgmc-weather.label", "dropdown-tgmc-weather.description", true, -20,
				new Dictionary<string, string>
				{
					{ "clear", "weather-clear" }, { "rain", "weather-rain" }, { "dust", "weather-dust" },
					{ "ash", "weather-ash" }, { "snow", "weather-snow" }, { "acidrain", "weather-acidrain" }
				}, WeatherDefault, false);

			yield return new LobbyBooleanOption(map, Options.Night,
				"checkbox-tgmc-night.label", "checkbox-tgmc-night.description", true, -20, NightDefault, false);

			yield return new LobbyBooleanOption(map, Options.LandingIntro,
				"checkbox-tgmc-landingintro.label", "checkbox-tgmc-landingintro.description", true, -19, LandingIntroDefault, false);

			yield return new LobbyBooleanOption(map, Options.TileStep,
				"checkbox-tgmc-tilestep.label", "checkbox-tgmc-tilestep.description", true, -15, TileStepDefault, false);

			yield return new LobbyOption(map, Options.Objective,
				"dropdown-tgmc-objective.label", "dropdown-tgmc-objective.description", true, -21,
				new Dictionary<string, string> { { "conquest", "objective-conquest" }, { "distress", "objective-distress" }, { "crash", "objective-crash" } }, ObjectiveDefault, false);

			yield return new LobbyOption(map, Options.LandingDelay,
				"dropdown-tgmc-landingdelay.label", "dropdown-tgmc-landingdelay.description", true, -21,
				new Dictionary<string, string> { { "0", "landingdelay-0" }, { "60", "landingdelay-60" }, { "120", "landingdelay-120" }, { "180", "landingdelay-180" } },
				LandingDelayDefault, false);

			yield return new LobbyBooleanOption(map, Options.Downed,
				"checkbox-tgmc-downed.label", "checkbox-tgmc-downed.description", true, -13, DownedDefault, false);

			yield return new LobbyBooleanOption(map, Options.Formation,
				"checkbox-tgmc-formation.label", "checkbox-tgmc-formation.description", true, -14, FormationDefault, false);
		}
	}

	// Turns the lobby's weather choice into a condition ("rain", "dust", "ash", "snow" or "acidrain") that the WeatherOverlay traits in world.yaml wait for.
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
			else if (weather == "ash")
				this.self.GrantCondition(info.AshCondition);
			else if (weather == "snow")
				this.self.GrantCondition(info.SnowCondition);
			else if (weather == "acidrain")
				this.self.GrantCondition(info.AcidRainCondition);
		}
	}

	[Desc("TGMC's landing delay (the lobby's Landing Delay): until it runs out, a unit of Factions that strays more than Radius cells from its " +
		"owner's start is turned back. The hive gets the first minutes to set up.")]
	public class LandingLeashInfo : TraitInfo
	{
		public readonly HashSet<string> Factions = ["marines", "som"];
		public readonly int Radius = 16;

		[Desc("Ticks between looks.")]
		public readonly int Interval = 25;

		public override object Create(ActorInitializer init) { return new LandingLeash(this); }
	}

	public class LandingLeash : ITick, INotifyCreated
	{
		readonly LandingLeashInfo info;
		int until;
		bool told;

		public LandingLeash(LandingLeashInfo info) { this.info = info; }

		void INotifyCreated.Created(Actor self)
		{
			var options = self.World.Map.Rules.Actors[SystemActors.World].TraitInfoOrDefault<TgmcOptionsInfo>();
			var seconds = int.TryParse(Options.Value(self.World, Options.LandingDelay, options?.LandingDelayDefault ?? "0"), out var v) ? v : 0;
			until = info.Factions.Contains(self.Owner.Faction.InternalName) ? seconds * 25 : 0;
		}

		void ITick.Tick(Actor self)
		{
			if (until == 0 || self.World.WorldTick >= until || (self.World.WorldTick + self.ActorID) % info.Interval != 0)
				return;

			// Ground units only: the landing intro's dropship and the air support fly in from the map edge.
			var move = self.TraitOrDefault<Mobile>();
			if (move == null)
				return;

			var home = self.Owner.HomeLocation;
			if ((self.Location - home).LengthSquared <= info.Radius * info.Radius)
				return;

			// Back toward the start, to the edge of the zone.
			var d = self.Location - home;
			var len = System.Math.Max(1, (int)System.Math.Sqrt(d.LengthSquared));
			var back = home + new CVec(d.X * (info.Radius - 2) / len, d.Y * (info.Radius - 2) / len);
			self.CancelActivity();
			self.QueueActivity(move.MoveTo(self.World.Map.Clamp(back), 2));

			// Once per unit, so a whole squad turned back says it once each and not every second.
			if (!told)
				TextNotificationsManager.AddTransientLine(self.Owner, "notification-landing-zone");

			told = true;
		}
	}

	[Desc("Grants Condition to this actor when the lobby's weather is one of Weathers: a snowstorm, sandstorm or ash fall cuts how far units see.")]
	public class GrantConditionOnWeatherInfo : TraitInfo
	{
		[FieldLoader.Require]
		[GrantedConditionReference]
		public readonly string Condition = null;

		public readonly HashSet<string> Weathers = [];

		public override object Create(ActorInitializer init) { return new GrantConditionOnWeather(this); }
	}

	public class GrantConditionOnWeather : INotifyCreated
	{
		readonly GrantConditionOnWeatherInfo info;

		public GrantConditionOnWeather(GrantConditionOnWeatherInfo info) { this.info = info; }

		void INotifyCreated.Created(Actor self)
		{
			var options = self.World.Map.Rules.Actors[SystemActors.World].TraitInfoOrDefault<TgmcOptionsInfo>();
			if (info.Weathers.Contains(Options.Value(self.World, Options.Weather, options?.WeatherDefault ?? "clear")))
				self.GrantCondition(info.Condition);
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
