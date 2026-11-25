#region Copyright & License Information
/*
 * TGMC mod for OpenRA. Personal, non-commercial.
 */
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.GameRules;
using OpenRA.Graphics;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Traits.Render;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	// The actor type the downed body stands for, so a revive brings back the same marine.
	public class DownedInit : ValueActorInit<string>, ISingleInstanceInit
	{
		public DownedInit(string value)
			: base(value) { }
	}

	[Desc("TGMC's downed state: a marine brought to zero health falls and lies there as a Downed actor, bleeding out, instead of dying at once. " +
		"Killed by one of DeathTypes (gibbed, melted, gassed) he dies outright. Off when the lobby's Downed option is off.")]
	public class DownableInfo : ConditionalTraitInfo
	{
		[ActorReference]
		public readonly string Actor = "downed";

		public readonly BitSet<DamageType> DeathTypes = default;

		[Desc("Health the downed body starts with, in percent: the bleed-out clock, and how much a corpsman has to heal.")]
		public readonly int StartHealth = 50;

		public override object Create(ActorInitializer init) { return new Downable(this); }
	}

	public class Downable : ConditionalTrait<DownableInfo>, INotifyKilled
	{
		public Downable(DownableInfo info)
			: base(info) { }

		public bool Downs(Actor self, AttackInfo e)
		{
			// A unit that kills itself (a chestburst, a script) dies outright.
			return !IsTraitDisabled && self.IsInWorld && e.Attacker != self && !e.Damage.DamageTypes.Overlaps(Info.DeathTypes)
				&& Options.Enabled(self.World, Options.Downed, true);
		}

		void INotifyKilled.Killed(Actor self, AttackInfo e)
		{
			if (!Downs(self, e))
				return;

			var owner = self.Owner;
			var cell = self.Location;
			var pos = self.CenterPosition;
			var facing = self.TraitOrDefault<IFacing>()?.Facing ?? WAngle.Zero;
			var type = self.Info.Name;
			self.World.AddFrameEndTask(w =>
			{
				if (owner.WinState == WinState.Lost)
					return;

				w.CreateActor(Info.Actor, new TypeDictionary
				{
					new LocationInit(cell),
					new CenterPositionInit(pos),
					new OwnerInit(owner),
					new FacingInit(facing),
					new DownedInit(type),
					new HealthInit(Info.StartHealth)
				});
			});
		}
	}

	[Desc("A downed marine. Bleeds out (a ChangesHealth with a negative Step on the same actor). Healed back to full health he stands up " +
		"again as his own unit at ReviveHealth percent. Killed by an actor with CocoonsDowned, a cocoon of the killer's side takes his place.")]
	public class DownedInfo : TraitInfo, Requires<HealthInfo>
	{
		[Desc("Health of the revived marine, in percent of his own.")]
		public readonly int ReviveHealth = 30;

		[Desc("The body's sequence on the marine's own image.")]
		public readonly string Sequence = "down";

		[Desc("Used when the marine's image has no Sequence.")]
		public readonly string FallbackSequence = "die";

		public readonly string Palette = "player";

		public override object Create(ActorInitializer init) { return new Downed(init, this); }
	}

	public class Downed : INotifyDamage, INotifyKilled, ITick, IRender, IAutoMouseBounds
	{
		readonly DownedInfo info;
		readonly Health health;
		readonly Animation body;
		readonly WithLingeringCorpseInfo corpse;
		readonly string image;
		public readonly string Type;
		bool done;

		public Downed(ActorInitializer init, DownedInfo info)
		{
			this.info = info;
			var self = init.Self;
			health = self.Trait<Health>();
			Type = init.GetValue<DownedInit, string>(info, null);
			var marine = Type != null ? self.World.Map.Rules.Actors[Type] : null;
			corpse = marine?.TraitInfoOrDefault<WithLingeringCorpseInfo>();
			image = marine?.TraitInfoOrDefault<RenderSpritesInfo>()?.GetImage(marine, self.Owner.Faction.InternalName);
			if (image == null)
				return;

			body = new Animation(self.World, image);
			var sequence = self.World.Map.Sequences.HasSequence(image, info.Sequence) ? info.Sequence : info.FallbackSequence;
			if (sequence == info.FallbackSequence)
				body.PlayFetchIndex(sequence, () => body.CurrentSequence.Length - 1);
			else
				body.PlayRepeating(sequence);
		}

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			if (done || self.IsDead || e.Damage.Value >= 0 || health.HP < health.MaxHP || Type == null)
				return;

			// Healed to full: he gets up.
			// shortcut: a new actor stands up, so the marine's veterancy is not kept; carry GainsExperience over if ranks start to matter.
			done = true;
			var owner = self.Owner;
			var cell = self.Location;
			var facing = self.TraitOrDefault<IFacing>()?.Facing ?? WAngle.Zero;
			self.World.AddFrameEndTask(w =>
			{
				if (self.IsDead || !self.IsInWorld)
					return;

				self.Dispose();
				w.CreateActor(Type, new TypeDictionary
				{
					new LocationInit(cell),
					new OwnerInit(owner),
					new FactionInit(owner.Faction.InternalName),
					new FacingInit(facing),
					new HealthInit(info.ReviveHealth)
				});
			});
		}

		void INotifyKilled.Killed(Actor self, AttackInfo e)
		{
			var pos = self.CenterPosition;
			var cocoons = e.Attacker != null && !e.Attacker.Disposed ? e.Attacker.Info.TraitInfoOrDefault<CocoonsDownedInfo>() : null;
			if (cocoons != null && e.Attacker.Owner.RelationshipWith(self.Owner) == PlayerRelationship.Enemy)
			{
				var owner = e.Attacker.Owner;
				var cell = self.Location;
				self.World.AddFrameEndTask(w => w.CreateActor(cocoons.Actor, new TypeDictionary
				{
					new LocationInit(cell),
					new OwnerInit(owner),
					new FactionInit(owner.Faction.InternalName)
				}));
				return;
			}

			// Bled out or finished off: the body stays where it lay, as any marine's does.
			if (corpse == null || image == null)
				return;

			var palette = corpse.DeathSequencePalette + (corpse.DeathPaletteIsPlayerPalette ? self.Owner.InternalName : "");
			self.World.AddFrameEndTask(w => w.Add(new LyingBody(pos, w, image, corpse.FallbackSequence, palette, corpse, false)));
		}

		void ITick.Tick(Actor self) { body?.Tick(); }

		IEnumerable<IRenderable> IRender.Render(Actor self, WorldRenderer wr)
		{
			if (body == null)
				return [];

			return body.Render(self.CenterPosition, wr.Palette(info.Palette + self.Owner.InternalName));
		}

		IEnumerable<Rectangle> IRender.ScreenBounds(Actor self, WorldRenderer wr)
		{
			return body == null ? [] : [body.ScreenBounds(wr, self.CenterPosition, WVec.Zero)];
		}

		Rectangle IAutoMouseBounds.AutoMouseoverBounds(Actor self, WorldRenderer wr)
		{
			return body == null ? Rectangle.Empty : body.ScreenBounds(wr, self.CenterPosition, WVec.Zero);
		}
	}

	[Desc("This xeno's killing blow on a downed enemy marine cocoons him: Actor (a cocoon of the xeno's side) takes his place.")]
	public class CocoonsDownedInfo : TraitInfo<CocoonsDowned>
	{
		[ActorReference]
		public readonly string Actor = "cocoon";
	}

	public class CocoonsDowned { }
}
