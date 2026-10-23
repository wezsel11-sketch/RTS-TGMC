#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using OpenRA.Effects;
using OpenRA.GameRules;
using OpenRA.Graphics;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Effects;
using OpenRA.Mods.Common.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC
{
	// Small helpers for the sound and sprite effects the traits in this assembly play.
	public static class Fx
	{
		public static void Sound(World world, WPos pos, string[] names)
		{
			if (names == null || names.Length == 0)
				return;

			Game.Sound.Play(SoundType.World, names[world.LocalRandom.Next(names.Length)], pos);
		}

		public static void Sprite(World world, WPos pos, string image, string sequence, string palette)
		{
			if (string.IsNullOrEmpty(image) || string.IsNullOrEmpty(sequence))
				return;

			world.AddFrameEndTask(w => w.Add(new SpriteEffect(pos, w, image, sequence, palette)));
		}

		/// <summary>A word shouted over a unit's head ("MOVE!"), floating up for a second and a half.</summary>
		public static void Shout(World world, Actor actor, string text, Color color)
		{
			if (string.IsNullOrEmpty(text))
				return;

			var pos = actor.CenterPosition + new WVec(0, 0, 1024);
			world.AddFrameEndTask(w => w.Add(new FloatingText(pos, color, text, 36)));
		}

		/// <summary>A ring that spreads from a spot out to a radius and fades: how far an aura or a screech reached.</summary>
		public static void Ring(World world, WPos pos, WDist radius, Color color)
		{
			if (radius.Length > 0)
				world.AddFrameEndTask(w => w.Add(new RingEffect(pos, radius, color)));
		}
	}

	sealed class RingEffect : IEffect, IEffectAnnotation
	{
		const int Ticks = 15;
		readonly WPos pos;
		readonly WDist radius;
		readonly Color color;
		int tick;

		public RingEffect(WPos pos, WDist radius, Color color)
		{
			this.pos = pos;
			this.radius = radius;
			this.color = color;
		}

		public void Tick(World world)
		{
			if (++tick >= Ticks)
				world.AddFrameEndTask(w => w.Remove(this));
		}

		public IEnumerable<IRenderable> Render(WorldRenderer wr) { return []; }

		public IEnumerable<IRenderable> RenderAnnotation(WorldRenderer wr)
		{
			var r = new WDist(radius.Length * tick / Ticks);
			yield return new CircleAnnotationRenderable(pos, r, 2, Color.FromArgb(255 * (Ticks - tick) / Ticks, color));
		}
	}
}

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("A host for a xeno embryo. The facehugger drops the host for a few seconds, then is spent. After that the host " +
		"counts down, crying out now and then, and bursts into a xeno larva for the infecting player unless it is healed first.")]
	public class InfestableInfo : TraitInfo
	{
		[Desc("Ticks from the facehugger latching on to the burst. 1500 is a minute.")]
		public readonly int BurstDelay = 1500;

		[Desc("Ticks the host lies helpless with the facehugger on its face. The facehugger dies when they end.")]
		public readonly int HugDuration = 100;

		[GrantedConditionReference]
		[Desc("Condition on the host while it is down. The marine rules show the fallen pose and pause its orders.")]
		public readonly string HugCondition = "hugged";

		[Desc("Condition given to the facehugger while it clings on. The facehugger rules pause and hide it from targeting.")]
		public readonly string LatchedCondition = "latched";

		[ActorReference]
		[Desc("Actor created for the infecting player when the host bursts.")]
		public readonly string Larva = "larva";

		[GrantedConditionReference]
		[Desc("Condition active while infected.")]
		public readonly string Condition = "infected";

		[Desc("Ticks between the host's cries while infected.")]
		public readonly int CryInterval = 100;

		[Desc("Sounds played when the facehugger latches on.")]
		public readonly string[] InfectSounds = [];

		[Desc("Sounds played now and then while infected.")]
		public readonly string[] CrySounds = [];

		[Desc("Sounds played when the host bursts.")]
		public readonly string[] BurstSounds = [];

		[Desc("Sounds played when the infection is cured.")]
		public readonly string[] CureSounds = [];

		[Desc("Effect image for the burst and the cure.")]
		public readonly string Image = "fx-infest";

		public readonly string BurstSequence = "burst";
		public readonly string CureSequence = "cure";
		public readonly string Palette = "effect";

		public override object Create(ActorInitializer init) { return new Infestable(this); }
	}

	public class Infestable : INotifyDamage, INotifyKilled, INotifyActorDisposing, ITick, ISelectionBar
	{
		readonly InfestableInfo info;
		int token = Actor.InvalidConditionToken;
		int hugToken = Actor.InvalidConditionToken;
		int countdown;
		int cryCountdown;
		int hugLeft;
		Player infector;
		Actor hugger;

		public Infestable(InfestableInfo info) { this.info = info; }

		public bool IsInfected => token != Actor.InvalidConditionToken;

		// A red bar that fills as the embryo grows toward the burst.
		float ISelectionBar.GetValue()
		{
			return IsInfected ? 1f - countdown / (float)System.Math.Max(1, info.BurstDelay) : 0f;
		}

		Color ISelectionBar.GetColor() { return Color.FromArgb(230, 70, 60); }
		bool ISelectionBar.DisplayWhenEmpty => false;

		/// <summary>Plants an embryo for `by`. The host drops with `facehugger` on its face. Returns false if the host
		/// already carries an embryo.</summary>
		public bool Infect(Actor self, Player by, Actor facehugger)
		{
			if (IsInfected || !Options.Enabled(self.World, Options.Infestation, true))
				return false;

			infector = by;

			// The lobby sets the minute between hug and burst; maps without a lobby keep BurstDelay.
			countdown = info.BurstDelay;
			if (self.World.LobbyInfo != null && int.TryParse(Options.Value(self.World, Options.BurstTime, ""), out var seconds) && info.BurstDelay == 1500)
				countdown = seconds * 25;
			cryCountdown = info.CryInterval;
			token = self.GrantCondition(info.Condition);
			Fx.Sound(self.World, self.CenterPosition, info.InfectSounds);

			// Tell the host's side, so a facehugged marine is not missed in the middle of a fight.
			TextNotificationsManager.AddTransientLine(self.Owner, "notification-infected");
			Traits.TgmcEventLog.Post(self.World, self.Owner, "event-facehugged", self.CenterPosition);
			Game.Sound.PlayToPlayer(SoundType.UI, self.Owner, "alert.ogg");
			var host = self;
			self.World.WorldActor.TraitOrDefault<RadarPings>()?.Add(
				() => host.Owner.IsAlliedWith(host.World.RenderPlayer), self.CenterPosition, Color.FromArgb(255, 70, 70), 75);

			// Drop the host: its orders stop, and the rules pause it and show it lying down while the condition holds.
			self.CancelActivity();
			hugLeft = info.HugDuration;
			hugToken = self.GrantCondition(info.HugCondition);

			// Seat the facehugger on the host's face and hold it there.
			if (facehugger != null && !facehugger.IsDead && !facehugger.Disposed)
			{
				hugger = facehugger;
				hugger.CancelActivity();
				hugger.TraitOrDefault<IPositionable>()?.SetCenterPosition(hugger, self.CenterPosition + new WVec(0, -160, 0));
				hugger.GrantCondition(info.LatchedCondition);
			}

			return true;
		}

		void ReleaseHost(Actor self)
		{
			if (hugToken != Actor.InvalidConditionToken)
				hugToken = self.RevokeCondition(hugToken);

			SpendHugger();
		}

		void SpendHugger()
		{
			var spent = hugger;
			hugger = null;
			if (spent == null)
				return;

			spent.World.AddFrameEndTask(w =>
			{
				// It dies on its own, with its death animation and sound, once its work is done.
				if (!spent.IsDead && !spent.Disposed)
					spent.Kill(spent);
			});
		}

		void INotifyKilled.Killed(Actor self, AttackInfo e) { SpendHugger(); }

		void INotifyActorDisposing.Disposing(Actor self) { SpendHugger(); }

		// Any healing at all clears the embryo.
		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			if (IsInfected && e.Damage.Value < 0)
				Cure(self);
		}

		void Cure(Actor self)
		{
			token = self.RevokeCondition(token);
			infector = null;
			ReleaseHost(self);
			Fx.Sound(self.World, self.CenterPosition, info.CureSounds);
			Fx.Sprite(self.World, self.CenterPosition, info.Image, info.CureSequence, info.Palette);
		}

		void ITick.Tick(Actor self)
		{
			if (!IsInfected)
				return;

			if (hugToken != Actor.InvalidConditionToken && --hugLeft <= 0)
				ReleaseHost(self);

			if (--cryCountdown <= 0)
			{
				cryCountdown = info.CryInterval;
				Fx.Sound(self.World, self.CenterPosition, info.CrySounds);
			}

			if (--countdown > 0)
				return;

			Burst(self);
		}

		void Burst(Actor self)
		{
			var world = self.World;
			var pos = self.CenterPosition;
			var cell = self.Location;
			var owner = infector ?? world.Players[0];
			var facing = world.SharedRandom.Next(0, 1024);

			token = Actor.InvalidConditionToken;
			infector = null;
			SpendHugger();

			Fx.Sound(world, pos, info.BurstSounds);
			Fx.Sprite(world, pos, info.Image, info.BurstSequence, info.Palette);
			TextNotificationsManager.AddTransientLine(self.Owner, "notification-burst");
			Traits.TgmcEventLog.Post(world, self.Owner, "event-burst", pos);
			Traits.TgmcEventLog.Post(world, owner, "event-larva", pos);

			self.Kill(self);

			// Queued after the kill, which frees the cell.
			world.AddFrameEndTask(w =>
			{
				w.CreateActor(info.Larva, new TypeDictionary
				{
					new LocationInit(cell),
					new OwnerInit(owner),
					new FactionInit(owner.Faction.InternalName),
					new FacingInit(new WAngle(facing))
				});
			});
		}
	}
}

namespace OpenRA.Mods.TGMC.Warheads
{
	[Desc("Plants a xeno embryo in an Infestable target. The firer stays on the host's face for a few seconds, then dies.")]
	public class InfestWarhead : Warhead
	{
		public override void DoImpact(in Target target, WarheadArgs args)
		{
			var source = args.SourceActor;
			if (source == null || target.Type != TargetType.Actor)
				return;

			var victim = target.Actor;
			if (!IsValidAgainst(victim, source))
				return;

			// The host holds the facehugger on its face and kills it once the host is back on its feet.
			victim.TraitOrDefault<Traits.Infestable>()?.Infect(victim, source.Owner, source);
		}
	}
}
