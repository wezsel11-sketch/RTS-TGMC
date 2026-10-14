#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose widgets this file extends.
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Widgets.Logic;
using OpenRA.Mods.TGMC.Traits;
using OpenRA.Traits;
using OpenRA.Widgets;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.World)]
	[Desc("Remembers the mod's notable events (facehugged, burst, evolved, egg hatched, CAS strike, ...) for the event log panel.")]
	public class TgmcEventLogInfo : TraitInfo
	{
		[Desc("How many events to keep.")]
		public readonly int Keep = 30;

		public override object Create(ActorInitializer init) { return new TgmcEventLog(this); }
	}

	public class TgmcEventLog
	{
		public readonly struct Entry
		{
			public readonly int Tick;
			public readonly Player Owner;
			public readonly string Text;
			public readonly WPos Position;

			public Entry(int tick, Player owner, string text, WPos position)
			{
				Tick = tick;
				Owner = owner;
				Text = text;
				Position = position;
			}
		}

		readonly TgmcEventLogInfo info;
		readonly List<Entry> entries = [];
		readonly Dictionary<(Player, string), int> counts = [];

		public TgmcEventLog(TgmcEventLogInfo info) { this.info = info; }

		public IReadOnlyList<Entry> Entries => entries;

		/// <summary>How many times `key` has been posted for `owner` this match; the end screen reads these.</summary>
		public int Count(Player owner, string key) => counts.TryGetValue((owner, key), out var n) ? n : 0;

		/// <summary>Records an event for `owner`'s side. `key` is a fluent message key.</summary>
		public static void Post(World world, Player owner, string key, WPos position)
		{
			var log = world.WorldActor.TraitOrDefault<TgmcEventLog>();
			if (log == null)
				return;

			log.counts[(owner, key)] = log.Count(owner, key) + 1;
			log.entries.Add(new Entry(world.WorldTick, owner, FluentProvider.GetMessage(key), position));
			if (log.entries.Count > log.info.Keep)
				log.entries.RemoveAt(0);
		}
	}
}

namespace OpenRA.Mods.TGMC.Widgets.Logic
{
	// The event log on the left: the latest events for your side, newest first. Click one to look at where it happened.
	public class EventLogLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public EventLogLogic(Widget widget, World world, WorldRenderer worldRenderer)
		{
			var log = world.WorldActor.TraitOrDefault<TgmcEventLog>();
			for (var i = 0; i < 6; i++)
			{
				var index = i;
				var button = widget.GetOrNull<ButtonWidget>($"EVENT_{i + 1}");
				if (button == null)
					continue;

				TgmcEventLog.Entry? Get()
				{
					if (log == null)
						return null;

					var viewer = world.LocalPlayer ?? world.RenderPlayer;
					var mine = log.Entries.Where(e => viewer == null || e.Owner == viewer || e.Owner.IsAlliedWith(viewer)).Reverse().ToList();
					return index < mine.Count ? mine[index] : null;
				}

				button.IsVisible = () => Get() != null;
				button.GetText = () =>
				{
					var e = Get();
					if (e == null)
						return "";

					var seconds = (world.WorldTick - e.Value.Tick) / 25;
					var age = seconds < 60 ? $"{seconds}s" : $"{seconds / 60}m";
					return $"[{age}] {e.Value.Text}";
				};
				button.OnClick = () =>
				{
					var e = Get();
					if (e != null)
						worldRenderer.Viewport.Center(e.Value.Position);
				};
			}
		}
	}

	// The end-of-match table: opens when you win or lose, one row per player.
	public class MatchStatsLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public MatchStatsLogic(Widget widget, World world)
		{
			var log = world.WorldActor.TraitOrDefault<TgmcEventLog>();
			var dismissed = false;
			var finishedAt = -1;

			var viewer = world.LocalPlayer;
			widget.IsVisible = () =>
			{
				if (dismissed || viewer == null || viewer.WinState == WinState.Undefined)
					return false;

				if (finishedAt < 0)
					finishedAt = world.WorldTick;

				return true;
			};

			widget.Get<LabelWidget>("STATS_TITLE").GetText = () =>
			{
				if (viewer == null)
					return "";

				var result = viewer.WinState == WinState.Won ? "Victory" : "Defeat";
				var seconds = (finishedAt >= 0 ? finishedAt : world.WorldTick) / 25;
				return $"{result}  -  {seconds / 60}:{seconds % 60:D2}";
			};

			widget.Get<ButtonWidget>("STATS_CLOSE").OnClick = () => dismissed = true;

			var players = world.Players.Where(p => p.Playable && !p.NonCombatant).ToList();
			for (var i = 0; i < 4; i++)
			{
				var row = i;
				Player P() => row < players.Count ? players[row] : null;
				string Cell(string id, Func<Player, string> text)
				{
					var player = P();
					return player == null ? "" : text(player);
				}

				void Bind(string id, Func<Player, string> text)
				{
					var label = widget.GetOrNull<LabelWidget>($"STATS_{id}_{row}");
					if (label != null)
						label.GetText = () => Cell(id, text);
				}

				Bind("NAME", p => p.PlayerName);
				Bind("KILLS", p => (p.PlayerActor.TraitOrDefault<PlayerStatistics>()?.UnitsKilled ?? 0).ToString());
				Bind("LOST", p => (p.PlayerActor.TraitOrDefault<PlayerStatistics>()?.UnitsDead ?? 0).ToString());
				Bind("HOSTS", p => (log?.Count(p, "event-facehugged") ?? 0).ToString());
				Bind("EVOLVED", p => (log?.Count(p, "event-evolved") ?? 0).ToString());
				Bind("CAS", p => (log?.Count(p, "event-cas") ?? 0).ToString());
			}
		}
	}

	// Buttons under the selection card: evolve and devolve the selected xenos, stop, and scatter.
	public class CommandCardLogic : ChromeLogic
	{
		readonly World world;

		[ObjectCreator.UseCtor]
		public CommandCardLogic(Widget widget, World world)
		{
			this.world = world;

			var evolve = widget.Get<ButtonWidget>("CMD_EVOLVE");
			evolve.IsDisabled = () => !Selected().Any(a => a.Info.TraitInfoOrDefault<EvolvesInfo>()?.Next != null);
			evolve.GetText = () => Label(true);
			evolve.OnClick = () => Issue(a => a.Info.TraitInfoOrDefault<EvolvesInfo>()?.Next != null, a => new Order("Evolve", a, false));

			var devolve = widget.Get<ButtonWidget>("CMD_DEVOLVE");
			devolve.IsDisabled = () => !Selected().Any(a => a.Info.TraitInfoOrDefault<EvolvesInfo>()?.Previous != null);
			devolve.GetText = () => Label(false);
			devolve.OnClick = () => Issue(a => a.Info.TraitInfoOrDefault<EvolvesInfo>()?.Previous != null, a => new Order("Evolve", a, true));

			var stop = widget.Get<ButtonWidget>("CMD_STOP");
			stop.IsDisabled = () => Selected().Count == 0;
			stop.OnClick = () => Issue(_ => true, a => new Order("Stop", a, false));

			foreach (var (id, stance) in new[] { ("CMD_AGGRESSIVE", UnitStance.AttackAnything), ("CMD_GUARD", UnitStance.Defend),
				("CMD_RETURN", UnitStance.ReturnFire), ("CMD_HOLD", UnitStance.HoldFire) })
			{
				var button = widget.GetOrNull<ButtonWidget>(id);
				if (button == null)
					continue;

				button.IsDisabled = () => !Selected().Any(a => a.TraitOrDefault<AutoTarget>() != null);
				button.IsHighlighted = () => Selected().Select(a => a.TraitOrDefault<AutoTarget>()).FirstOrDefault(t => t != null)?.Stance == stance;
				button.OnClick = () => Issue(a => a.TraitOrDefault<AutoTarget>() != null,
					a => new Order("SetUnitStance", a, false) { ExtraData = (uint)stance });
			}

			// Send the hurt and the infected among the selection to the nearest Medbay or corpsman.
			var medic = widget.GetOrNull<ButtonWidget>("CMD_MEDIC");
			if (medic != null)
			{
				medic.IsDisabled = () => !Selected().Any(NeedsMedic);
				medic.OnClick = () =>
				{
					foreach (var a in Selected().Where(NeedsMedic))
					{
						var healer = world.Actors
							.Where(h => h.Owner == a.Owner && h.IsInWorld && !h.IsDead && h != a && (h.Info.Name == "medbay" || h.Info.Name == "medic"))
							.OrderBy(h => (h.CenterPosition - a.CenterPosition).LengthSquared)
							.FirstOrDefault();
						if (healer != null)
							world.IssueOrder(new Order("Move", a, Target.FromCell(world, healer.Location), false));
					}
				};
			}

			// Select every infected marine you own, wherever he is.
			var infected = widget.GetOrNull<ButtonWidget>("CMD_INFECTED");
			if (infected != null)
			{
				infected.IsDisabled = () => !Infected().Any();
				infected.OnClick = () => world.Selection.Combine(world, Infected().ToList(), false, false);
			}

			// Caste abilities (Rage, Acid Spray, Fling, huggers...): two buttons that show whatever the selection can do, with a cooldown.
			foreach (var slot in new[] { 1, 2 })
			{
				var button = widget.GetOrNull<ButtonWidget>("CMD_ABILITY" + slot);
				if (button == null)
					continue;

				var s = slot;
				button.IsVisible = () => Abilities(s).Any();
				button.IsDisabled = () => !Abilities(s).Any(x => x.Ready);
				button.IsHighlighted = () => Abilities(s).Any(x => x.Active);
				button.GetText = () => AbilityLabel(Abilities(s).FirstOrDefault());
				button.OnClick = () => Issue(a => a.TraitsImplementing<ActiveAbility>().Any(x => x.Info.Slot == s && x.Ready),
					a => new Order(a.TraitsImplementing<ActiveAbility>().First(x => x.Info.Slot == s && x.Ready).Info.OrderName, a, false));
			}

			var scatter = widget.Get<ButtonWidget>("CMD_SCATTER");
			scatter.IsDisabled = () => Selected().Count == 0;
			scatter.OnClick = () => Issue(a => a.Info.HasTraitInfo<MobileInfo>(), a => new Order("Scatter", a, false));

			// Evolving is a xeno thing and the medic buttons are a marine thing: each side sees only its own, and Stop and
			// Scatter slide into the first row's free places for the marines.
			var faction = world.LocalPlayer?.Faction.InternalName;
			if (faction == "marines")
			{
				evolve.IsVisible = () => false;
				devolve.IsVisible = () => false;
				stop.Bounds = evolve.Bounds;
				scatter.Bounds = devolve.Bounds;
			}
			else if (faction == "xenos")
			{
				if (medic != null)
					medic.IsVisible = () => false;

				if (infected != null)
					infected.IsVisible = () => false;
			}
		}

		IEnumerable<ActiveAbility> Abilities(int slot)
		{
			return Selected().SelectMany(a => a.TraitsImplementing<ActiveAbility>()).Where(x => x.Info.Slot == slot && !x.IsTraitDisabled);
		}

		static string AbilityLabel(ActiveAbility a)
		{
			if (a == null)
				return "";

			if (a.Info.Charges > 1)
				return $"{a.Info.Label} {a.ChargesLeft}/{a.Info.Charges}";

			if (a.Active)
				return a.Info.Label + "!";

			return a.CooldownRemaining > 0 ? $"{a.Info.Label} {(a.CooldownRemaining + 24) / 25}s" : a.Info.Label;
		}

		static bool NeedsMedic(Actor a)
		{
			var health = a.TraitOrDefault<IHealth>();
			return a.TraitOrDefault<Infestable>()?.IsInfected == true
				|| (health != null && a.Info.HasTraitInfo<InfestableInfo>() && health.HP < health.MaxHP * 6 / 10);
		}

		IEnumerable<Actor> Infected()
		{
			return world.ActorsWithTrait<Infestable>()
				.Where(p => p.Actor.Owner == world.LocalPlayer && p.Actor.IsInWorld && !p.Actor.IsDead && p.Trait.IsInfected)
				.Select(p => p.Actor);
		}

		List<Actor> Selected()
		{
			return world.Selection.Actors.Where(a => a.IsInWorld && !a.IsDead && a.Owner == world.LocalPlayer).ToList();
		}

		void Issue(System.Func<Actor, bool> which, System.Func<Actor, Order> order)
		{
			foreach (var a in Selected().Where(which))
				world.IssueOrder(order(a));
		}

		// "Evolve: Hunter" when one caste is selected, so the player sees what the button does.
		string Label(bool evolving)
		{
			var castes = Selected()
				.Select(a => a.Info.TraitInfoOrDefault<EvolvesInfo>())
				.Select(e => evolving ? e?.Next : e?.Previous)
				.Where(n => n != null).Distinct().ToList();

			var verb = evolving ? "Evolve" : "Devolve";
			if (castes.Count != 1)
				return verb;

			var tooltip = world.Map.Rules.Actors[castes[0]].TraitInfoOrDefault<TooltipInfo>();
			var name = tooltip != null ? FluentProvider.GetMessage(tooltip.Name).Replace("Xeno ", "") : castes[0];
			return $"{verb}: {name}";
		}
	}
}

namespace OpenRA.Mods.TGMC.Widgets
{
	using OpenRA.Mods.Common.Traits;

	[Desc("Keypad keys that step the selected units one cell, a way to walk a single marine around like in SS13.")]
	public class StepKeysWidget : Widget
	{
		static readonly (string Hotkey, int Dx, int Dy)[] Steps =
		[
			("TgmcStepN", 0, -1), ("TgmcStepS", 0, 1), ("TgmcStepW", -1, 0), ("TgmcStepE", 1, 0),
			("TgmcStepNW", -1, -1), ("TgmcStepNE", 1, -1), ("TgmcStepSW", -1, 1), ("TgmcStepSE", 1, 1),
		];

		readonly World world;
		readonly ModData modData;

		[ObjectCreator.UseCtor]
		public StepKeysWidget(World world, ModData modData)
		{
			this.world = world;
			this.modData = modData;
		}

		public override bool HandleKeyPress(KeyInput e)
		{
			if (e.Event != KeyInputEvent.Down || world.LocalPlayer == null || world.IsGameOver)
				return false;

			foreach (var (name, dx, dy) in Steps)
			{
				if (Hotkey.FromKeyInput(e) != modData.Hotkeys[name].GetValue())
					continue;

				foreach (var a in world.Selection.Actors.Where(a => a.Owner == world.LocalPlayer && a.IsInWorld && !a.IsDead && a.TraitOrDefault<IMove>() != null))
				{
					var cell = a.World.Map.Clamp(a.Location + new CVec(dx, dy));
					world.IssueOrder(new Order("Move", a, Target.FromCell(world, cell), false));
				}

				return true;
			}

			return false;
		}
	}
}

namespace OpenRA.Mods.TGMC.Widgets
{
	using System.Linq;
	using OpenRA.Mods.Common.Traits;
	using OpenRA.Mods.TGMC.Traits;
	using OpenRA.Traits;
	using OpenRA.Widgets;

	[Desc("Smart selection hotkeys: idle combat units, wounded or infected units, and every unit of the selected type anywhere on the map.")]
	public class SmartSelectWidget : Widget
	{
		readonly World world;
		readonly ModData modData;

		[ObjectCreator.UseCtor]
		public SmartSelectWidget(World world, ModData modData)
		{
			this.world = world;
			this.modData = modData;
		}

		bool Pressed(KeyInput e, string name)
		{
			return Hotkey.FromKeyInput(e) == modData.Hotkeys[name].GetValue();
		}

		public override bool HandleKeyPress(KeyInput e)
		{
			if (e.Event != KeyInputEvent.Down || world.LocalPlayer == null || world.IsGameOver)
				return false;

			var mine = world.Actors.Where(a => a.Owner == world.LocalPlayer && a.IsInWorld && !a.IsDead && a.Info.HasTraitInfo<MobileInfo>()
				&& a.Info.HasTraitInfo<AttackBaseInfo>() && a.Info.HasTraitInfo<SelectableInfo>()).ToList();

			if (Pressed(e, "TgmcSelectIdle"))
				return Select(mine.Where(a => a.IsIdle), e);

			if (Pressed(e, "TgmcSelectWounded"))
				return Select(mine.Where(a => a.TraitOrDefault<Infestable>()?.IsInfected == true
					|| (a.TraitOrDefault<IHealth>() is { } h && h.HP < h.MaxHP * 6 / 10)), e);

			if (Pressed(e, "TgmcSelectAllOfType"))
			{
				var types = world.Selection.Actors.Where(a => a.Owner == world.LocalPlayer).Select(a => a.Info.Name).ToHashSet();
				return Select(mine.Where(a => types.Contains(a.Info.Name)), e);
			}

			return false;
		}

		bool Select(System.Collections.Generic.IEnumerable<Actor> actors, KeyInput e)
		{
			var list = actors.ToList();
			if (list.Count == 0)
				return true;

			world.Selection.Combine(world, list, e.Modifiers.HasModifier(Modifiers.Shift), false);
			return true;
		}
	}
}

namespace OpenRA.Mods.TGMC.Widgets.Logic
{
	using OpenRA.Mods.Common.Widgets.Logic;

	[Desc("Dev aid: with the environment variable TGMC_MENU_SHOT set, takes a screenshot of the main menu a few seconds after it opens.")]
	public class MenuShotLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public MenuShotLogic(Widget widget)
		{
			if (System.Environment.GetEnvironmentVariable("TGMC_MENU_SHOT") != null)
				Game.RunAfterDelay(4000, Game.TakeScreenshot);
		}
	}
}
