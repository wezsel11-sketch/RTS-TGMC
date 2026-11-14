#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose widgets this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Orders;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Widgets.Logic;
using OpenRA.Mods.TGMC.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;
using OpenRA.Widgets;

namespace OpenRA.Mods.TGMC.Widgets.Logic
{
	// Fills the selection card in the sidebar: who is selected, their health, ammunition and condition.
	public class SelectionReadoutLogic : ChromeLogic
	{
		static readonly string[] Tiers = ["Young", "Mature", "Elder", "Ancient"];

		readonly World world;

		[ObjectCreator.UseCtor]
		public SelectionReadoutLogic(Widget widget, World world)
		{
			this.world = world;

			widget.Get<LabelWidget>("SEL_NAME").GetText = Name;
			widget.Get<LabelWidget>("SEL_HEALTH").GetText = Health;
			widget.Get<LabelWidget>("SEL_AMMO").GetText = Ammo;
			widget.Get<LabelWidget>("SEL_STATUS").GetText = Status;

			var hpBar = widget.GetOrNull<ProgressBarWidget>("SEL_HPBAR");
			if (hpBar != null)
			{
				hpBar.IsVisible = () => Selected().Count > 0;
				hpBar.GetPercentage = () =>
				{
					var healths = Selected().Select(a => a.TraitOrDefault<IHealth>()).Where(x => x != null).ToList();
					var max = healths.Sum(x => x.MaxHP);
					return HealthTint.Apply(hpBar, max == 0 ? 0 : 100 * healths.Sum(x => x.HP) / max);
				};
			}

			// The right half of the card for one unit: its rank (or a xeno's maturity) with a bar to the next, what it fights with, and its record.
			bool One() => Selected().Count == 1;
			if (widget.GetOrNull<LabelWidget>("SEL_RANK") is { } rank)
			{
				rank.IsVisible = One;
				rank.GetText = () => Rank(out _, out _).Text;
				rank.GetColor = () => Rank(out _, out _).Color;
			}

			if (widget.GetOrNull<ProgressBarWidget>("SEL_XPBAR") is { } xp)
			{
				xp.IsVisible = () => One() && Rank(out _, out _).Progress >= 0;
				xp.GetPercentage = () =>
				{
					var r = Rank(out var maturity, out _);
					xp.Bar = maturity ? "progressbar-thumb-maturity" : "progressbar-thumb-xp";
					return r.Progress;
				};
			}

			if (widget.GetOrNull<LabelWidget>("SEL_WEAPON") is { } weapon)
			{
				weapon.IsVisible = One;
				weapon.GetText = Weapons;
			}

			if (widget.GetOrNull<LabelWidget>("SEL_RECORD") is { } record)
			{
				record.IsVisible = One;
				record.GetText = Record;
			}

			var portrait = widget.GetOrNull<SpriteWidget>("SEL_PORTRAIT");
			if (portrait != null)
			{
				portrait.GetSprite = Portrait;

				// Big sprites (the mech) shrink to fit the frame.
				portrait.GetScale = () =>
				{
					var sprite = Portrait();
					return sprite == null ? 1f : System.Math.Min(1f, System.Math.Min(portrait.Bounds.Width / sprite.Size.X, portrait.Bounds.Height / sprite.Size.Y));
				};
			}
		}

		// The unit's production icon, shown larger beside its name.
		Sprite Portrait()
		{
			var selected = Selected();
			if (selected.Count == 0)
				return null;

			var name = selected.GroupBy(a => a.Info.Name).OrderByDescending(g => g.Count()).First().Key;
			return Icons.Of(world, name);
		}

		List<Actor> Selected()
		{
			return world.Selection.Actors.Where(a => a.IsInWorld && !a.IsDead).ToList();
		}

		string Name()
		{
			var selected = Selected();
			if (selected.Count == 0)
				return "Nothing selected";

			if (selected.Count > 1)
			{
				var groups = selected.GroupBy(a => a.Info.Name).OrderByDescending(g => g.Count()).ToList();
				return groups.Count == 1 ? $"{selected.Count} {Title(groups[0].First())}" : $"{selected.Count} units";
			}

			return Title(selected[0]);
		}

		static string Title(Actor a)
		{
			var tooltip = a.Info.TraitInfoOrDefault<TooltipInfo>();
			return tooltip != null ? FluentProvider.GetMessage(tooltip.Name) : a.Info.Name;
		}

		string Health()
		{
			var healths = Selected().Select(a => a.TraitOrDefault<IHealth>()).Where(h => h != null).ToList();
			if (healths.Count == 0)
				return "";

			return $"Health {healths.Sum(h => h.HP)} / {healths.Sum(h => h.MaxHP)}";
		}

		static readonly Color Unranked = Color.FromArgb(150, 150, 150);
		static readonly Dictionary<string, Color> RankColors = new()
		{
			{ "veteran", Color.FromArgb(192, 192, 192) }, { "hardened", Color.FromArgb(224, 192, 96) }, { "elite", Color.FromArgb(255, 208, 64) }
		};

		// The selected unit's rank line: marines by experience (GainsExperience), xenos by maturity. Progress is the share of the way to
		// the next rank, or -1 when there is no bar to show (top rank, or a unit that does neither).
		(string Text, Color Color, int Progress) Rank(out bool maturity, out int level)
		{
			maturity = false;
			level = 0;
			var selected = Selected();
			if (selected.Count != 1)
				return ("", Unranked, -1);

			var a = selected[0];
			var gains = a.TraitOrDefault<GainsExperience>();
			if (gains != null)
			{
				var info = a.Info.TraitInfo<GainsExperienceInfo>();
				var scale = info.ExperienceModifier < 0 ? (a.Info.TraitInfoOrDefault<ValuedInfo>()?.Cost ?? 1) : info.ExperienceModifier;
				var steps = info.Conditions.OrderBy(kv => kv.Key).ToList();
				level = gains.Level;
				var name = level == 0 ? "Recruit" : Capitalise(steps[level - 1].Value.Replace("rank-", ""));
				var colour = level == 0 ? Unranked : RankColors.GetValueOrDefault(steps[level - 1].Value.Replace("rank-", ""), Color.White);
				if (level >= steps.Count)
					return ($"{name.ToUpperInvariant()}   top rank", colour, -1);

				// Experience is in hundredths of the unit's cost: show it as requisition worth of kills.
				var from = level == 0 ? 0 : steps[level - 1].Key * scale;
				var to = steps[level].Key * scale;
				var progress = 100 * (gains.Experience - from) / System.Math.Max(1, to - from);
				return ($"{name.ToUpperInvariant()}   {gains.Experience / 100} / {to / 100} to {Capitalise(steps[level].Value.Replace("rank-", ""))}", colour, progress);
			}

			var ripe = a.TraitOrDefault<Maturity>();
			if (ripe != null && !ripe.IsTraitDisabled)
			{
				maturity = true;
				level = ripe.Tier;
				var tiers = ripe.Info.Conditions.Length;
				var colour = Color.FromArgb(200, 140, 235);
				if (level >= tiers)
					return ($"{Tiers[level].ToUpperInvariant()}   fully grown", colour, -1);

				var progress = (int)(100 * ((ISelectionBar)ripe).GetValue());
				return ($"{Tiers[level].ToUpperInvariant()}   {progress}% to {Tiers[level + 1]}", colour, progress);
			}

			return ("", Unranked, -1);
		}

		static string Capitalise(string s) { return s.Length == 0 ? s : char.ToUpperInvariant(s[0]) + s[1..]; }

		// The weapons the unit fights with now (a mech's loadout or a toggled shell type switches some off): name, damage, reach, rate.
		string Weapons()
		{
			var selected = Selected();
			if (selected.Count != 1)
				return "";

			var lines = selected[0].TraitsImplementing<Armament>()
				.Where(arm => !arm.IsTraitDisabled && arm.Weapon.Warheads.OfType<Mods.Common.Warheads.DamageWarhead>().Any())
				.GroupBy(arm => arm.Info.Weapon)
				// The main gun first: the one that reaches furthest, then a melee or side weapon.
				.OrderByDescending(g => g.First().Weapon.Range.Length)
				.Take(2)
				.Select(g =>
				{
					var w = g.First().Weapon;
					var damage = w.Warheads.OfType<Mods.Common.Warheads.DamageWarhead>().First().Damage;
					var cycle = w.ReloadDelay + w.BurstDelays.Take(System.Math.Max(0, w.Burst - 1)).Sum();
					var perSecond = cycle > 0 ? System.Math.Abs(damage) * w.Burst * 25 / cycle : 0;
					var reach = w.Range.Length < 1536 ? "melee" : $"{w.Range.Length / 1024f:0.#} cells";
					return $"{g.Key.Replace("TGMC", "")}  {System.Math.Abs(damage)}x{w.Burst}  {reach}  {perSecond}/s" + (damage < 0 ? " heal" : "");
				});
			return string.Join("     ", lines);
		}

		// Armour, speed and the unit's kills so far.
		string Record()
		{
			var selected = Selected();
			if (selected.Count != 1)
				return "";

			var a = selected[0];
			var parts = new List<string>();
			if (a.Info.TraitInfoOrDefault<ArmorInfo>()?.Type is { } armour)
				parts.Add($"Armour {armour}");

			if (a.TraitOrDefault<IMove>() != null && a.Info.TraitInfoOrDefault<MobileInfo>() is { } mobile)
				parts.Add($"Speed {mobile.Speed}");

			if (a.TraitOrDefault<KillCount>() is { } kills && (kills.Kills > 0 || a.TraitOrDefault<AttackBase>() != null))
				parts.Add(kills.Kills == 1 ? "1 kill" : $"{kills.Kills} kills");

			// A building that earns: what it pays now. A disabled miner's trickle is switched off: say so, and how to bring it back.
			var trickles = a.TraitsImplementing<CashTrickler>().ToList();
			if (trickles.Count > 0)
			{
				var paying = trickles.Where(t => !t.IsTraitDisabled && !t.IsTraitPaused).Sum(t => t.Info.Amount * 1500 / System.Math.Max(1, t.Info.Interval));
				parts.Add(paying > 0 ? $"Income +{paying}/min" : a.TraitOrDefault<MinerField>() != null ? "DISABLED: repair it to earn again" : "Earns nothing now");
			}

			return string.Join("   ", parts);
		}

		string Ammo()
		{
			var selected = Selected();
			if (selected.Count != 1)
				return "";

			var pools = selected[0].TraitsImplementing<AmmoPool>().ToList();
			if (pools.Count == 0)
				return "";

			return string.Join("   ", pools.Select(p => p.CurrentAmmoCount == 0
				? "Reloading..."
				: $"Ammo {p.CurrentAmmoCount} / {p.Info.Ammo}"));
		}

		string Status()
		{
			var selected = Selected();
			if (selected.Count != 1)
				return "";

			var a = selected[0];
			var notes = new List<string>();

			var maturity = a.TraitOrDefault<Maturity>();
			if (maturity != null && maturity.Tier > 0)
				notes.Add($"{Tiers[maturity.Tier]} xeno");

			var pounce = a.TraitOrDefault<Pounce>();
			if (pounce != null && !pounce.IsTraitDisabled)
				notes.Add(pounce.CooldownRemaining > 0 ? $"Leap {(pounce.CooldownRemaining + 24) / 25}s" : "Leap ready");

			var reflex = a.TraitOrDefault<Reflex>();
			if (reflex != null && !reflex.IsTraitDisabled)
				notes.Add(reflex.CooldownRemaining > 0 ? $"Evade {(reflex.CooldownRemaining + 24) / 25}s" : "Evade ready");

			if (a.TraitOrDefault<Infestable>()?.IsInfected == true)
				notes.Add("INFECTED - needs a medic");

			if (a.TraitOrDefault<Evolves>() is Evolves)
			{
				var evolves = a.Info.TraitInfoOrDefault<EvolvesInfo>();
				if (evolves?.Next != null)
					notes.Add("F: evolve");
			}

			return string.Join("   ", notes);
		}
	}
}

namespace OpenRA.Mods.TGMC.Traits
{
	using System;
	using OpenRA.Primitives;

	[Desc("Counts the enemies this actor has killed, for the selection card.")]
	public class KillCountInfo : TraitInfo
	{
		public override object Create(ActorInitializer init) { return new KillCount(); }
	}

	public class KillCount : INotifyAppliedDamage
	{
		public int Kills { get; private set; }

		void INotifyAppliedDamage.AppliedDamage(Actor self, Actor damaged, AttackInfo e)
		{
			if (e.DamageState == DamageState.Dead && e.PreviousDamageState != DamageState.Dead
				&& self.Owner.RelationshipWith(damaged.Owner) == PlayerRelationship.Enemy)
				Kills++;
		}
	}

	[Desc("A bar under a selected unit showing how much of its magazine is left.")]
	public class AmmoBarInfo : TraitInfo, Requires<AmmoPoolInfo>
	{
		[Desc("Which ammo pool to show.")]
		public readonly string AmmoPool = "primary";

		public readonly Color Color = Color.FromArgb(235, 190, 60);

		public override object Create(ActorInitializer init) { return new AmmoBar(init.Self, this); }
	}

	public class AmmoBar : ISelectionBar
	{
		readonly AmmoBarInfo info;
		readonly AmmoPool pool;

		public AmmoBar(Actor self, AmmoBarInfo info)
		{
			this.info = info;
			pool = self.TraitsImplementing<AmmoPool>().FirstOrDefault(p => p.Info.Name == info.AmmoPool);
		}

		float ISelectionBar.GetValue()
		{
			return pool == null ? 0f : pool.CurrentAmmoCount / (float)Math.Max(1, pool.Info.Ammo);
		}

		Color ISelectionBar.GetColor() { return info.Color; }
		bool ISelectionBar.DisplayWhenEmpty => true;
	}
}

namespace OpenRA.Mods.TGMC.Traits
{
	using System.Collections.Generic;
	using OpenRA.Graphics;
	using OpenRA.Mods.Common.Graphics;
	using OpenRA.Primitives;

	[Desc("A ring under a selected actor that breathes in and out, so you can always see what you have selected. " +
		"Your own units get a green ring, others a red one.")]
	public class SelectionRingInfo : TraitInfo
	{
		public readonly WDist Radius = new(560);

		[Desc("How far the ring swells and shrinks, and how many ticks one breath takes.")]
		public readonly WDist Swell = new(70);
		public readonly int Period = 40;

		public readonly Color OwnColor = Color.FromArgb(220, 110, 255, 120);
		public readonly Color OtherColor = Color.FromArgb(220, 255, 90, 80);

		public override object Create(ActorInitializer init) { return new SelectionRing(this); }
	}

	public class SelectionRing : IRenderAnnotationsWhenSelected
	{
		readonly SelectionRingInfo info;

		public SelectionRing(SelectionRingInfo info) { this.info = info; }

		bool IRenderAnnotationsWhenSelected.SpatiallyPartitionable => false;

		IEnumerable<IRenderable> IRenderAnnotationsWhenSelected.RenderAnnotations(Actor self, WorldRenderer wr)
		{
			var own = self.Owner == self.World.LocalPlayer;
			var phase = (self.World.WorldTick % info.Period) * 2 * System.Math.PI / info.Period;
			var radius = info.Radius.Length + (int)(info.Swell.Length * System.Math.Sin(phase));
			yield return new CircleAnnotationRenderable(self.CenterPosition, new WDist(radius), 2,
				own ? info.OwnColor : info.OtherColor);
		}
	}
}

namespace OpenRA.Mods.TGMC.Traits
{
	using System.Linq;

	[TraitLocation(SystemActors.World)]
	[Desc("For testing: at a given tick selects the local player's actors of some types and takes a screenshot, so a headless " +
		"run can show what the HUD looks like. Does nothing unless a map's rules add it.")]
	public class ScreenshotAtInfo : TraitInfo
	{
		public readonly int Tick = 100;

		[Desc("More ticks to take a screenshot on. mod/shots.sh joins them all into one filmstrip, to judge an effect's timing.")]
		public readonly int[] Also = [];

		public readonly string[] Select = [];

		[Desc("Buttons to click just before the shot, by widget id (for example HELP_BUTTON).")]
		public readonly string[] Click = [];

		[Desc("Command card buttons to right-click (autocast) and to hold the mouse over (the range preview), at the click tick.")]
		public readonly string[] RightClick = [];
		public readonly string[] Hover = [];

		[Desc("Tick to click the buttons on. 0 means five ticks before the shot.")]
		public readonly int ClickTick = 0;

		[Desc("A building to start placing (the ghost) at the click tick, as if its palette icon were clicked.")]
		public readonly string Place = null;

		[Desc("If above 0, takes the shot this many interface frames after the local player's game ends (the world stops ticking then).")]
		public readonly int AfterGameOver = 0;

		public override object Create(ActorInitializer init) { return new ScreenshotAt(this); }
	}

	public class ScreenshotAt : ITick, IWorldLoaded
	{
		readonly ScreenshotAtInfo info;
		WorldRenderer worldRenderer;
		int ticks;

		bool placeNow;

		void IWorldLoaded.WorldLoaded(World w, WorldRenderer wr)
		{
			worldRenderer = wr;
			if (info.Place == null && info.AfterGameOver <= 0)
				return;

			var overFrames = 0;

			// The order generator may only change outside the simulation, so a widget does it on its own tick.
			var ticker = new LogicTickerWidget
			{
				OnTick = () =>
				{
					if (info.AfterGameOver > 0 && w.LocalPlayer != null && w.LocalPlayer.WinState != WinState.Undefined && ++overFrames == info.AfterGameOver)
						Game.TakeScreenshot();

					if (!placeNow)
						return;

					placeNow = false;
					var queue = w.LocalPlayer.PlayerActor.TraitsImplementing<ProductionQueue>().First(q => q.Info.Type == "MarineBuild");
					w.OrderGenerator = new PlaceBuildingOrderGenerator(queue, info.Place, worldRenderer);
				}
			};
			OpenRA.Widgets.Ui.Root.AddChild(ticker);
		}

		public ScreenshotAt(ScreenshotAtInfo info) { this.info = info; }

		void ITick.Tick(Actor self)
		{
			ticks++;
			var world = self.World;
			var selectTick = System.Math.Max(1, (info.ClickTick > 0 ? System.Math.Min(info.ClickTick, info.Tick) : info.Tick) - 10);
			if (ticks == selectTick && world.LocalPlayer != null)
			{
				foreach (var a in world.Actors.Where(a => a.Owner == world.LocalPlayer && a.IsInWorld && info.Select.Contains(a.Info.Name)))
					world.Selection.Add(a);
			}

			if (ticks == (info.ClickTick > 0 ? info.ClickTick : info.Tick - 5))
			{
				foreach (var id in info.Click)
					OpenRA.Widgets.Ui.Root.GetOrNull<OpenRA.Mods.Common.Widgets.ButtonWidget>(id)?.OnClick();
				foreach (var id in info.RightClick)
					OpenRA.Widgets.Ui.Root.GetOrNull<OpenRA.Mods.TGMC.Widgets.AbilityButtonWidget>(id)?.OnRightClick();
				foreach (var id in info.Hover)
					OpenRA.Widgets.Ui.Root.GetOrNull<OpenRA.Mods.TGMC.Widgets.AbilityButtonWidget>(id)?.OnHover(true);
			}

			if (info.Place != null && ticks == (info.ClickTick > 0 ? info.ClickTick : info.Tick - 5))
				placeNow = true;

			if (ticks == info.Tick || info.Also.Contains(ticks))
				Game.TakeScreenshot();
		}
	}
}

namespace OpenRA.Mods.TGMC.Traits
{
	using System.Collections.Generic;
	using OpenRA.Graphics;
	using OpenRA.Mods.Common.Graphics;
	using OpenRA.Primitives;

	[Desc("A short word over the actor's head while a condition holds (RequiresCondition), such as INFECTED or STUNNED. " +
		"Several on one actor stack up by Line.")]
	public class StatusLabelInfo : ConditionalTraitInfo
	{
		[FieldLoader.Require]
		public readonly string Text = null;

		public readonly Color Color = Color.White;

		[Desc("Stacking row: 0 is lowest.")]
		public readonly int Line = 0;

		[Desc("Height of the lowest row above the actor's centre.")]
		public readonly WDist Height = new(720);

		[Desc("Only show while the actor is selected.")]
		public readonly bool OnlyWhenSelected = false;

		public override object Create(ActorInitializer init) { return new StatusLabel(this); }
	}

	public class StatusLabel : ConditionalTrait<StatusLabelInfo>, IRenderAnnotations
	{
		public StatusLabel(StatusLabelInfo info)
			: base(info) { }

		bool IRenderAnnotations.SpatiallyPartitionable => true;

		IEnumerable<IRenderable> IRenderAnnotations.RenderAnnotations(Actor self, WorldRenderer wr)
		{
			if (IsTraitDisabled || !self.IsInWorld || self.World.FogObscures(self))
				yield break;

			if (Info.OnlyWhenSelected && !self.World.Selection.Contains(self))
				yield break;

			if (!Game.Renderer.Fonts.TryGetValue("TinyBold", out var font))
				yield break;

			var pos = self.CenterPosition - new WVec(0, Info.Height.Length + Info.Line * 200, 0);
			yield return new TextAnnotationRenderable(font, pos, 0, Info.Color, Info.Text);
		}
	}
}

namespace OpenRA.Mods.TGMC.Widgets.Logic
{
	using System.Linq;
	using OpenRA.Mods.Common.Traits;
	using OpenRA.Mods.Common.Widgets;
	using OpenRA.Mods.Common.Widgets.Logic;
	using OpenRA.Widgets;

	// The slim bar across the top: requisition income per minute, army size, and for the xenos how many larvae are waiting.
	public class TopBarLogic : ChromeLogic
	{
		readonly World world;
		int cachedTick = -100;
		string income = "";
		string army = "";

		[ObjectCreator.UseCtor]
		public TopBarLogic(Widget widget, World world)
		{
			this.world = world;
			widget.Get<LabelWidget>("TOP_INCOME").GetText = () => { Refresh(); return income; };
			widget.Get<LabelWidget>("TOP_ARMY").GetText = () => { Refresh(); return army; };
		}

		void Refresh()
		{
			// Counting every actor is not free: once a second is plenty.
			if (world.WorldTick - cachedTick < 25)
				return;

			cachedTick = world.WorldTick;
			var player = world.LocalPlayer ?? world.RenderPlayer;
			if (player == null)
			{
				income = army = "";
				return;
			}

			var perMinute = 0;
			foreach (var p in world.ActorsWithTrait<CashTrickler>().Where(p => p.Actor.Owner == player && !p.Trait.IsTraitDisabled))
				perMinute += p.Trait.Info.Amount * 1500 / System.Math.Max(1, p.Trait.Info.Interval);

			var units = world.ActorsHavingTrait<IMove>().Count(a => a.Owner == player && a.IsInWorld && !a.IsDead);
			var larvae = world.Actors.Count(a => a.Owner == player && a.IsInWorld && !a.IsDead && a.Info.Name == "larva");

			income = $"Income +{perMinute}/min";
			army = larvae > 0 ? $"Army {units}   Larvae {larvae}" : $"Army {units}";
		}
	}

	// A thin bar along the bottom of each production tab button: green for how far the first item in that tab's queues has come, full
	// gold when something there is done and waiting (a building to place). So an upgrade or a building shows its progress from any tab.
	public class ProductionTabProgressLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public ProductionTabProgressLogic(Widget widget, World world)
		{
			foreach (var button in widget.Children.OfType<ProductionTypeButtonWidget>())
			{
				var bar = button.GetOrNull<ProgressBarWidget>("PROGRESS");
				if (bar == null)
					continue;

				var group = button.ProductionGroup;
				IEnumerable<ProductionItem> Items() => world.LocalPlayer == null ? [] : world.LocalPlayer.PlayerActor.TraitsImplementing<ProductionQueue>()
					.Where(q => q.Enabled && (q.Info.Group ?? q.Info.Type) == group)
					.SelectMany(q => q.AllQueued());

				bar.IsVisible = () => Items().Any(i => i.Started);
				bar.GetPercentage = () =>
				{
					var items = Items().ToList();
					if (items.Any(i => i.Done))
					{
						bar.Bar = "progressbar-thumb-xp";
						return 100;
					}

					bar.Bar = "progressbar-thumb";
					var first = items.FirstOrDefault(i => i.Started && !i.Paused);
					return first == null || first.TotalTime == 0 ? 0 : 100 - 100 * first.RemainingTime / first.TotalTime;
				};
			}
		}
	}

	// Above the selection card: when several units are selected, a small icon for each with a health bar. Click one to select
	// only that unit; Shift-click drops it from the selection.
	public class GroupGridLogic : ChromeLogic
	{
		const int Cells = 16;

		readonly World world;

		[ObjectCreator.UseCtor]
		public GroupGridLogic(Widget widget, World world)
		{
			this.world = world;
			widget.IsVisible = () => Members().Count > 1;

			for (var i = 0; i < Cells; i++)
			{
				var index = i;
				var button = widget.Get<ButtonWidget>($"GRP_{i}");
				var icon = button.Get<SpriteWidget>($"GRP_ICON_{i}");
				var hp = button.Get<ProgressBarWidget>($"GRP_HP_{i}");

				Actor At() => index < Members().Count ? Members()[index] : null;

				button.IsVisible = () => At() != null;
				icon.GetSprite = () =>
				{
					var a = At();
					return a == null ? null : Icons.Of(world, a.Info.Name);
				};

				// Production icons are 64x48; shrink them into the cell.
				icon.GetScale = () =>
				{
					var sprite = icon.GetSprite();
					return sprite == null ? 1f : System.Math.Min(1f, System.Math.Min(icon.Bounds.Width / sprite.Size.X, icon.Bounds.Height / sprite.Size.Y));
				};

				hp.GetPercentage = () =>
				{
					var health = At()?.TraitOrDefault<IHealth>();
					return HealthTint.Apply(hp, health == null || health.MaxHP == 0 ? 0 : 100 * health.HP / health.MaxHP);
				};

				button.OnClick = () =>
				{
					var a = At();
					if (a == null)
						return;

					if (Game.GetModifierKeys().HasModifier(Modifiers.Shift))
						world.Selection.Remove(a);
					else
						world.Selection.Combine(world, [a], false, true);
				};
			}
		}

		// Selected units in a steady order, grouped by type, so the cells do not shuffle as health changes.
		List<Actor> Members()
		{
			return world.Selection.Actors.Where(a => a.IsInWorld && !a.IsDead).OrderBy(a => a.Info.Name).ThenBy(a => a.ActorID).Take(Cells).ToList();
		}
	}

	// The ? button and the / key (F1 is the first production hotkey): a panel listing the mod's controls.
	public class HelpOverlayLogic : ChromeLogic
	{
		[ObjectCreator.UseCtor]
		public HelpOverlayLogic(Widget widget)
		{
			var panel = widget.Parent.Get("HELP_PANEL");
			var button = widget as ButtonWidget;
			panel.IsVisible = () => button.IsHighlighted();
			var open = false;
			button.IsHighlighted = () => open;
			button.OnClick = () => open = !open;
		}
	}

	// A health bar that turns amber and then red as the unit is hurt (the three bar tiles come from make_chrome.py).
	static class Icons
	{
		// An actor's production icon, or null. HasSequence throws for an image with no sequences at all
		// (the mirage decoy wears the rifleman's image), so ask for the image first.
		public static Sprite Of(World world, string actor)
		{
			var sequences = world.Map.Sequences;
			return sequences.Images.Contains(actor) && sequences.HasSequence(actor, "icon") ? sequences.GetSequence(actor, "icon").GetSprite(0) : null;
		}
	}

	static class HealthTint
	{
		public static int Apply(ProgressBarWidget bar, int percent)
		{
			bar.Bar = percent > 60 ? "progressbar-thumb" : percent > 30 ? "progressbar-thumb-mid" : "progressbar-thumb-low";
			return percent;
		}
	}
}
