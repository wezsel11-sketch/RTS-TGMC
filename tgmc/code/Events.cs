#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose widgets this file extends.
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Orders;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Widgets.Logic;
using OpenRA.Mods.TGMC.Orders;
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
		readonly Dictionary<(Player, string), int> lastPosted = [];

		public TgmcEventLog(TgmcEventLogInfo info) { this.info = info; }

		public IReadOnlyList<Entry> Entries => entries;

		/// <summary>How many times `key` has been posted for `owner` this match; the end screen reads these.</summary>
		public int Count(Player owner, string key) => counts.TryGetValue((owner, key), out var n) ? n : 0;

		/// <summary>Like Post, but skipped if `key` was already posted for `owner` within the last `cooldownTicks`. Returns whether it posted.</summary>
		public static bool PostLimited(World world, Player owner, string key, WPos position, int cooldownTicks)
		{
			var log = world.WorldActor.TraitOrDefault<TgmcEventLog>();
			if (log == null)
				return false;

			if (log.lastPosted.TryGetValue((owner, key), out var last) && world.WorldTick - last < cooldownTicks)
				return false;

			log.lastPosted[(owner, key)] = world.WorldTick;
			Post(world, owner, key, position);
			return true;
		}

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

	// The command card, Warcraft style: a fixed row (attack-move, stop, patrol, stance) and eight slots that fill with what the
	// selected unit type can do: its abilities on their own slots, then evolve/devolve, retreat, and the medic buttons while
	// someone needs them.
	public class CommandCardLogic : ChromeLogic
	{
		// What one slot button shows and does.
		sealed class Entry
		{
			public string Text;
			public string Tooltip;
			public bool Disabled;
			public bool Highlighted;
			public Action Click;
		}

		const int Slots = 8;
		static readonly (UnitStance Stance, string Name)[] Stances =
		{
			(UnitStance.AttackAnything, "Aggressive"), (UnitStance.Defend, "Guard"), (UnitStance.ReturnFire, "Return fire"), (UnitStance.HoldFire, "Hold fire")
		};

		readonly World world;
		Entry[] entries = new Entry[Slots];
		int entriesTick = -1;

		[ObjectCreator.UseCtor]
		public CommandCardLogic(Widget widget, World world)
		{
			this.world = world;

			// Row one shows its keys in the tooltip too.
			static string Keyed(string text, string hotkey)
			{
				var key = Game.ModData.Hotkeys[hotkey].GetValue();
				return key.IsValid() ? $"{text} [{key.DisplayString()}]" : text;
			}

			var stop = widget.Get<ButtonWidget>("CMD_STOP");
			stop.GetTooltipText = () => Keyed("Stop", "Stop");
			stop.IsDisabled = () => Selected().Count == 0;
			stop.OnClick = () => Issue(_ => true, a => new Order("Stop", a, false));

			// Attack: classic attack-move, the same as the attack-move key (Ctrl for assault move, as in OpenRA).
			var attack = widget.Get<ButtonWidget>("CMD_ATTACK");
			attack.IsDisabled = () => Selected().Count == 0;
			attack.IsHighlighted = () => world.OrderGenerator is AttackMoveOrderGenerator;
			attack.GetTooltipText = () => Keyed("Attack-move: walk there, fighting what you meet", "AttackMove");
			attack.OnClick = () => world.OrderGenerator = new AttackMoveOrderGenerator(world, Selected());

			// Patrol: the unit walks between where it stands and the cell you pick.
			var patrol = widget.Get<ButtonWidget>("CMD_PATROL");
			patrol.IsDisabled = () => Selected().Count == 0;
			patrol.IsHighlighted = () => world.OrderGenerator is PatrolOrderGenerator;
			patrol.GetTooltipText = () => "Patrol between here and the cell you pick";
			patrol.OnClick = () => world.OrderGenerator = new PatrolOrderGenerator(world, Selected());

			// One stance button that steps through the four; the four stance keys still set one directly (zero-size buttons).
			var stance = widget.Get<ButtonWidget>("CMD_STANCE");
			stance.IsDisabled = () => !Selected().Any(a => a.TraitOrDefault<AutoTarget>() != null);
			stance.GetText = () => "Stance\n" + Stances.FirstOrDefault(s => s.Stance == CurrentStance()).Name;
			stance.GetTooltipText = () => "Cycle the stance: Aggressive, Guard, Return fire, Hold fire";
			stance.OnClick = () => SetStance(Stances[(Array.FindIndex(Stances, s => s.Stance == CurrentStance()) + 1) % Stances.Length].Stance);
			foreach (var (id, s) in new[] { ("CMD_AGGRESSIVE", UnitStance.AttackAnything), ("CMD_GUARD", UnitStance.Defend),
				("CMD_RETURN", UnitStance.ReturnFire), ("CMD_HOLD", UnitStance.HoldFire) })
			{
				var button = widget.GetOrNull<ButtonWidget>(id);
				if (button != null)
					button.OnClick = () => SetStance(s);
			}

			var retreatKey = widget.GetOrNull<ButtonWidget>("CMD_RETREAT");
			if (retreatKey != null)
				retreatKey.OnClick = Retreat;

			for (var i = 0; i < Slots; i++)
			{
				var button = widget.Get<ButtonWidget>("CMD_SLOT" + (i + 1));
				var n = i;
				var key = button.Key;
				button.IsVisible = () => Entries()[n] != null;
				button.IsDisabled = () => Entries()[n]?.Disabled ?? true;
				button.IsHighlighted = () => Entries()[n]?.Highlighted ?? false;
				// The hotkey goes in the tooltip, not on the button, to keep the buttons small.
				button.GetText = () => Entries()[n]?.Text ?? "";
				button.GetTooltipText = () => Entries()[n]?.Tooltip + (key.GetValue().IsValid() ? $" [{key.GetValue().DisplayString()}]" : "");
				button.OnClick = () => Entries()[n]?.Click();
			}
		}

		// Built once per tick: the slot buttons ask for it many times a frame.
		Entry[] Entries()
		{
			if (entriesTick == world.WorldTick && !world.Paused)
				return entries;

			entriesTick = world.WorldTick;
			entries = new Entry[Slots];
			var selected = Selected();

			// The card shows the unit type with the most units selected; ties go to the one selected first.
			var units = selected.GroupBy(a => a.Info.Name).OrderByDescending(g => g.Count()).FirstOrDefault()?.ToList();
			if (units == null)
				return entries;

			foreach (var ability in units[0].TraitsImplementing<ActiveAbility>().Where(x => !x.IsTraitDisabled))
			{
				var slot = ability.Info.Slot - 1;
				if (slot < 0 || slot >= Slots || entries[slot] != null)
					continue;

				var order = ability.Info.OrderName;
				var mine = units
					.Select(u => (Unit: u, Ability: u.TraitsImplementing<ActiveAbility>().FirstOrDefault(x => x.Info.OrderName == order && !x.IsTraitDisabled)))
					.Where(x => x.Ability != null).ToList();
				var shown = mine.Select(x => x.Ability).FirstOrDefault(x => x.Ready) ?? ability;
				entries[slot] = new Entry
				{
					Text = AbilityLabel(shown),
					Tooltip = (ability.Info.Description ?? ability.Info.Label) + $" (cooldown {(ability.Info.Cooldown + 24) / 25} s)",
					Disabled = !mine.Any(x => x.Ability.Ready),
					Highlighted = mine.Any(x => x.Ability.Active)
						|| (world.OrderGenerator is AbilityOrderGenerator g && g.OrderName == order),
					Click = () =>
					{
						// An aimed ability waits for the click that says where.
						if (ability.IsAimed)
						{
							world.OrderGenerator = new AbilityOrderGenerator(world, mine.Select(x => x.Unit), ability.Info);
							return;
						}

						var queued = Game.GetModifierKeys().HasModifier(Modifiers.Shift);
						foreach (var x in mine.Where(x => x.Ability.Ready))
							world.IssueOrder(new Order(order, x.Unit, queued));
					}
				};
			}

			if (selected.Any(a => a.Info.TraitInfoOrDefault<EvolvesInfo>()?.Next != null))
				AddSide(Label(true).Replace(": ", "\n"), "Evolve into the next caste", () =>
					Issue(a => a.Info.TraitInfoOrDefault<EvolvesInfo>()?.Next != null, a => new Order("Evolve", a, false)));

			if (selected.Any(a => a.Info.TraitInfoOrDefault<EvolvesInfo>()?.Previous != null))
				AddSide(Label(false).Replace(": ", "\n"), "Devolve into the previous caste", () =>
					Issue(a => a.Info.TraitInfoOrDefault<EvolvesInfo>()?.Previous != null, a => new Order("Evolve", a, true)));

			if (selected.Any(a => a.TraitOrDefault<Retreat>() != null))
				AddSide("Retreat", "Send the selected units back to the nearest return point", Retreat);

			if (selected.Any(NeedsMedic))
				AddSide("To medic", "Send the hurt and the infected to the nearest Medbay or corpsman", ToMedic);

			if (selected.Any(a => a.Info.HasTraitInfo<InfestableInfo>()) && Infected().Any())
				AddSide("Infected", "Select every infected marine you own", () => world.Selection.Combine(world, Infected().ToList(), false, false));

			return entries;
		}

		// A side button takes the first free slot; with none free it is left off the card.
		void AddSide(string text, string tooltip, Action click)
		{
			var free = Array.IndexOf(entries, null);
			if (free >= 0)
				entries[free] = new Entry { Text = text, Tooltip = tooltip, Click = click };
		}

		void Retreat()
		{
			Issue(a => a.TraitOrDefault<Retreat>() != null, a => new Order(Traits.Retreat.OrderName, a, Game.GetModifierKeys().HasModifier(Modifiers.Shift)));
		}

		// Send the hurt and the infected among the selection to the nearest Medbay or corpsman.
		void ToMedic()
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
		}

		UnitStance CurrentStance()
		{
			return Selected().Select(a => a.TraitOrDefault<AutoTarget>()).FirstOrDefault(t => t != null)?.Stance ?? UnitStance.AttackAnything;
		}

		void SetStance(UnitStance stance)
		{
			Issue(a => a.TraitOrDefault<AutoTarget>() != null, a => new Order("SetUnitStance", a, false) { ExtraData = (uint)stance });
		}

		static string AbilityLabel(ActiveAbility a)
		{
			if (a == null)
				return "";

			// The name, then a second line with what the player needs to know right now.
			if (a.Info.Charges > 1)
				return $"{a.Info.Label}\n{a.ChargesLeft}/{a.Info.Charges}";

			if (a.Active)
				return a.Info.Label + "\nON";

			if (a.CooldownRemaining > 0)
				return $"{a.Info.Label}\n{(a.CooldownRemaining + 24) / 25}s";

			return a.Info.PlasmaCost > 0 ? $"{a.Info.Label}\n{a.Info.PlasmaCost} plasma" : a.Info.Label;
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

namespace OpenRA.Mods.TGMC.Widgets.Logic
{
	// The Repeat button on the build panel: toggles repeat build on every unit queue of the local player. Its hotkey is TgmcRepeatBuild.
	public class RepeatBuildLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public RepeatBuildLogic(Widget widget, World world)
		{
			var button = widget.Get<ButtonWidget>("REPEAT_BUILD");
			var player = world.LocalPlayer;
			if (player == null)
				return;

			IEnumerable<OpenRA.Mods.TGMC.Traits.MultiProductionQueue> Queues() => player.PlayerActor.TraitsImplementing<OpenRA.Mods.TGMC.Traits.MultiProductionQueue>();

			button.IsHighlighted = () => Queues().Any(q => q.Repeat);
			button.OnClick = () =>
			{
				var on = !button.IsHighlighted();
				foreach (var q in Queues())
					q.Repeat = on;
			};
		}
	}
}
