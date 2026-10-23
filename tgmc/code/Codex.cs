#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose widgets this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Widgets.Logic;
using OpenRA.Mods.TGMC.Traits;
using OpenRA.Traits;
using OpenRA.Widgets;

namespace OpenRA.Mods.TGMC.Widgets.Logic
{
	// The Codex: every unit and building of both sides, with its stats read from the rules, so it never goes out of date.
	public class CodexLogic : ChromeLogic
	{
		readonly World world;
		ActorInfo selected;

		[ObjectCreator.UseCtor]
		public CodexLogic(Widget widget, World world)
		{
			this.world = world;
			var panel = widget.Parent.Get("CODEX_PANEL");
			var button = (ButtonWidget)widget;
			var open = false;
			button.IsHighlighted = () => open;
			button.OnClick = () => open = !open;
			panel.IsVisible = () => open;

			var list = panel.Get<ScrollPanelWidget>("CODEX_LIST");
			var template = list.Get<ScrollItemWidget>("CODEX_ITEM");
			list.RemoveChildren();

			var entries = Entries().ToList();
			selected = entries.FirstOrDefault();
			foreach (var ai in entries)
			{
				var actor = ai;
				var item = ScrollItemWidget.Setup(template, () => selected == actor, () => selected = actor);
				item.Get<LabelWidget>("NAME").GetText = () => (Side(actor) == "xenos" ? "X  " : "M  ") + Title(actor);
				list.AddChild(item);
			}

			panel.Get<LabelWidget>("CODEX_TITLE").GetText = () => selected == null ? "" : Title(selected);
			panel.Get<LabelWidget>("CODEX_DESC").GetText = () => Description(selected);
			panel.Get<LabelWidget>("CODEX_STATS").GetText = () => Stats(selected);
			var portrait = panel.GetOrNull<SpriteWidget>("CODEX_PORTRAIT");
			if (portrait != null)
			{
				portrait.GetSprite = () =>
				{
					if (selected == null || !world.Map.Sequences.HasSequence(selected.Name, "icon"))
						return null;

					return world.Map.Sequences.GetSequence(selected.Name, "icon").GetSprite(0);
				};
				portrait.GetScale = () =>
				{
					var sprite = portrait.GetSprite();
					return sprite == null ? 1f : System.Math.Min(2f, System.Math.Min(portrait.Bounds.Width / sprite.Size.X, portrait.Bounds.Height / sprite.Size.Y));
				};
			}
		}

		IEnumerable<ActorInfo> Entries()
		{
			return world.Map.Rules.Actors.Values
				.Where(ai => !ai.Name.StartsWith('^') && ai.HasTraitInfo<TooltipInfo>()
					&& (ai.HasTraitInfo<BuildableInfo>() || ai.HasTraitInfo<EvolvesInfo>()))
				.OrderBy(ai => Side(ai))
				.ThenBy(ai => ai.HasTraitInfo<BuildingInfo>() ? 1 : 0)
				.ThenBy(ai => ai.TraitInfoOrDefault<BuildableInfo>()?.BuildPaletteOrder ?? 0);
		}

		static string Side(ActorInfo ai)
		{
			var queue = ai.TraitInfoOrDefault<BuildableInfo>()?.Queue.FirstOrDefault() ?? "Xeno";
			return queue.StartsWith("Xeno") ? "xenos" : "marines";
		}

		static string Title(ActorInfo ai)
		{
			var tooltip = ai.TraitInfoOrDefault<TooltipInfo>();
			return tooltip != null ? FluentProvider.GetMessage(tooltip.Name) : ai.Name;
		}

		static string Description(ActorInfo ai)
		{
			var key = ai?.TraitInfoOrDefault<BuildableInfo>()?.Description;
			return key == null ? "" : FluentProvider.GetMessage(key);
		}

		string Stats(ActorInfo ai)
		{
			if (ai == null)
				return "";

			var lines = new List<string>();
			var hp = ai.TraitInfoOrDefault<HealthInfo>()?.HP ?? 0;
			var cost = ai.TraitInfoOrDefault<ValuedInfo>()?.Cost ?? 0;
			var speed = ai.TraitInfoOrDefault<MobileInfo>()?.Speed;
			var armor = ai.TraitInfoOrDefault<ArmorInfo>()?.Type;
			lines.Add($"Health {hp}    Cost {cost}" + (speed != null ? $"    Speed {speed}" : "") + (armor != null ? $"    Armour {armor}" : ""));

			foreach (var armament in ai.TraitInfos<ArmamentInfo>())
			{
				if (!world.Map.Rules.Weapons.TryGetValue(armament.Weapon.ToLowerInvariant(), out var weapon))
					continue;

				var damage = weapon.Warheads.OfType<DamageWarhead>().Select(w => w.Damage).FirstOrDefault();
				var cycle = weapon.ReloadDelay + weapon.BurstDelays.Take(System.Math.Max(0, weapon.Burst - 1)).Sum();
				var perSecond = cycle > 0 ? System.Math.Abs(damage) * weapon.Burst * 25 / cycle : 0;
				var kind = damage < 0 ? "heals" : "damage";
				lines.Add($"{armament.Weapon.Replace("TGMC", "")}: {kind} {System.Math.Abs(damage)} x{weapon.Burst}, range {weapon.Range.Length / 1024f:0.#} cells, about {perSecond}/s");
			}

			var buildable = ai.TraitInfoOrDefault<BuildableInfo>();
			// "~faction-marines" and the like are hidden prerequisites (which side may build it), not something to build first.
			var needs = buildable?.Prerequisites.Where(p => !p.StartsWith('~')).ToList() ?? [];
			if (needs.Count > 0)
				lines.Add("Needs: " + string.Join(", ", needs.Select(p => world.Map.Rules.Actors.TryGetValue(p, out var pa) ? Title(pa) : p)));

			// What this building unlocks: everything buildable that lists it as a prerequisite.
			var unlocks = world.Map.Rules.Actors.Values
				.Where(a => !a.Name.StartsWith('^') && a.TraitInfoOrDefault<BuildableInfo>() is { } b
					&& b.Prerequisites.Any(p => string.Equals(p, ai.Name, System.StringComparison.OrdinalIgnoreCase)))
				.Select(Title).Distinct().OrderBy(t => t).ToList();
			if (unlocks.Count > 0)
				lines.Add("Unlocks: " + string.Join(", ", unlocks));

			// The unit's command card abilities, as its slot buttons show them.
			var abilities = ai.TraitInfos<ActiveAbilityInfo>().OrderBy(a => a.Slot).ToList();
			if (abilities.Count > 0)
				lines.Add("Abilities:\n" + string.Join("\n", abilities.Select(a => $"  {a.Label}: {a.Description ?? ""}"
					+ (a.Cooldown > 0 ? $" ({(a.Cooldown + 24) / 25} s)" : "") + (a.PlasmaCost > 0 ? $" [{a.PlasmaCost} plasma]" : ""))));

			var evolves = ai.TraitInfoOrDefault<EvolvesInfo>();
			if (evolves != null && (evolves.Next != null || evolves.Previous != null))
				lines.Add("Evolves to: " + (evolves.Next != null ? Title(world.Map.Rules.Actors[evolves.Next]) : "-")
					+ "    from: " + (evolves.Previous != null ? Title(world.Map.Rules.Actors[evolves.Previous]) : "-"));

			return string.Join("\n", lines);
		}
	}
}
