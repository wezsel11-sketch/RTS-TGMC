#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Traits.Render;
using OpenRA.Primitives;
using OpenRA.Scripting;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("A xeno that grows stronger with age: each tier is a condition (mature, elder, ancient) the rules turn into " +
		"bonuses. Age only builds while the owner has the required structure, like TGMC's Maturity Tower.")]
	public class MaturityInfo : ConditionalTraitInfo
	{
		[Desc("Ticks of age at which each tier starts.")]
		public readonly int[] Ticks = [1500, 3000, 4500];

		[Desc("Condition granted at each tier. Each stays on when the next arrives.")]
		public readonly string[] Conditions = ["mature", "elder", "ancient"];

		[Desc("The owner must have this prerequisite for the xeno to age. Empty means it always ages.")]
		public readonly string Prerequisite = "maturity-tower";

		[Desc("Sounds and effect played at each new tier.")]
		public readonly string[] Sounds = [];
		public readonly string Image = "fx-infest";
		public readonly string Sequence = "evolve";
		public readonly string Palette = "effect";

		[GrantedConditionReference]
		public IEnumerable<string> GrantedConditions => Conditions;

		public override object Create(ActorInitializer init) { return new Maturity(this); }
	}

	public class Maturity : ConditionalTrait<MaturityInfo>, ITick, ISelectionBar
	{
		int age;
		int checkCountdown;
		bool aging = true;
		readonly List<int> tokens = [];

		public Maturity(MaturityInfo info)
			: base(info) { }

		/// <summary>0 for a young xeno, up to the number of tiers.</summary>
		public int Tier => tokens.Count;

		// A purple bar for the age toward the next tier.
		float ISelectionBar.GetValue()
		{
			if (IsTraitDisabled || Tier >= Info.Conditions.Length)
				return 0f;

			var from = Tier == 0 ? 0 : Info.Ticks[Tier - 1];
			var span = System.Math.Max(1, Info.Ticks[Tier] - from);
			return System.Math.Clamp((age - from) / (float)span, 0f, 1f);
		}

		Color ISelectionBar.GetColor() { return Color.FromArgb(190, 110, 230); }
		bool ISelectionBar.DisplayWhenEmpty => false;

		void ITick.Tick(Actor self)
		{
			if (IsTraitDisabled || Tier >= Info.Conditions.Length || !Options.Enabled(self.World, Options.Maturity, true))
				return;

			// Looking up prerequisites is not free, so ask twice a second.
			if (--checkCountdown <= 0)
			{
				checkCountdown = 12;
				aging = string.IsNullOrEmpty(Info.Prerequisite)
					|| self.Owner.PlayerActor.Trait<TechTree>().HasPrerequisites([Info.Prerequisite]);
			}

			if (!aging)
				return;

			age++;
			if (age >= Info.Ticks[Tier])
			{
				tokens.Add(self.GrantCondition(Info.Conditions[Tier]));
				Fx.Sound(self.World, self.CenterPosition, Info.Sounds);
				Fx.Sprite(self.World, self.CenterPosition, Info.Image, Info.Sequence, Info.Palette);
				TgmcEventLog.Post(self.World, self.Owner, "event-matured", self.CenterPosition);
			}
		}
	}

	[Desc("Evasion: when this actor is hurt it grants itself a condition for a moment (the rules make that slower to " +
		"hit and faster), then has to wait out the cooldown. After the Runner's Evasion in TGMC.")]
	public class ReflexInfo : ConditionalTraitInfo
	{
		[GrantedConditionReference]
		public readonly string Condition = "evading";

		[Desc("Ticks the condition lasts.")]
		public readonly int Duration = 60;

		[Desc("Ticks before it can trigger again.")]
		public readonly int Cooldown = 250;

		[Desc("Sounds played as it triggers.")]
		public readonly string[] Sounds = [];

		public override object Create(ActorInitializer init) { return new Reflex(this); }
	}

	public class Reflex : ConditionalTrait<ReflexInfo>, INotifyDamage, ITick
	{
		int cooldown;
		int left;
		int token = Actor.InvalidConditionToken;

		public Reflex(ReflexInfo info)
			: base(info) { }

		public int CooldownRemaining => cooldown;

		void INotifyDamage.Damaged(Actor self, AttackInfo e)
		{
			if (IsTraitDisabled || cooldown > 0 || e.Damage.Value <= 0 || e.Attacker == null)
				return;

			if (self.Owner.RelationshipWith(e.Attacker.Owner) != PlayerRelationship.Enemy)
				return;

			cooldown = Info.Cooldown;
			left = Info.Duration;
			if (token == Actor.InvalidConditionToken)
				token = self.GrantCondition(Info.Condition);

			Fx.Sound(self.World, self.CenterPosition, Info.Sounds);
		}

		void ITick.Tick(Actor self)
		{
			if (cooldown > 0)
				cooldown--;

			if (token != Actor.InvalidConditionToken && --left <= 0)
				token = self.RevokeCondition(token);
		}
	}

	[Desc("A xeno egg. When an enemy marine comes near it opens and a facehugger hops out, then it stays empty while the " +
		"next one grows. Draws its own open and empty sequences.")]
	public class HuggerEggInfo : ConditionalTraitInfo
	{
		[ActorReference]
		public readonly string Actor = "facehugger";

		[Desc("How close an enemy must come.")]
		public readonly WDist Radius = WDist.FromCells(3);

		[Desc("Ticks from one hugger to the next, and (a fifth of it) before the first.")]
		public readonly int Cooldown = 625;

		[Desc("Target type an enemy must have.")]
		public readonly string TargetType = "Infestable";

		[GrantedConditionReference]
		[Desc("Condition active while a hugger is ready inside.")]
		public readonly string ReadyCondition = "hugger-ready";

		public readonly string OpenSequence = "open";
		public readonly string EmptySequence = "empty";

		public readonly string[] Sounds = [];

		public override object Create(ActorInitializer init) { return new HuggerEgg(this); }
	}

	public class HuggerEgg : ConditionalTrait<HuggerEggInfo>, ITick
	{
		int cooldown;
		int readyToken = Actor.InvalidConditionToken;

		public HuggerEgg(HuggerEggInfo info)
			: base(info)
		{
			cooldown = info.Cooldown / 5;
		}

		public bool IsReady => readyToken != Actor.InvalidConditionToken;

		void ITick.Tick(Actor self)
		{
			if (IsTraitDisabled)
				return;

			if (!IsReady)
			{
				if (--cooldown <= 0)
				{
					readyToken = self.GrantCondition(Info.ReadyCondition);
					self.TraitOrDefault<WithSpriteBody>()?.CancelCustomAnimation(self);
				}

				return;
			}

			var tripped = self.World.FindActorsInCircle(self.CenterPosition, Info.Radius)
				.Any(a => !a.IsDead && self.Owner.RelationshipWith(a.Owner) == PlayerRelationship.Enemy
					&& a.GetEnabledTargetTypes().Contains(Info.TargetType));

			if (tripped)
				Hatch(self);
		}

		void Hatch(Actor self)
		{
			var world = self.World;
			var owner = self.Owner;
			var cell = FreeCellNear(self);
			if (cell == null)
				return;

			readyToken = self.RevokeCondition(readyToken);
			cooldown = Info.Cooldown;
			Fx.Sound(world, self.CenterPosition, Info.Sounds);
			TgmcEventLog.Post(world, owner, "event-egg", self.CenterPosition);

			var body = self.TraitOrDefault<WithSpriteBody>();
			body?.PlayCustomAnimation(self, Info.OpenSequence, () => body.PlayCustomAnimationRepeating(self, Info.EmptySequence));

			var spot = cell.Value;
			world.AddFrameEndTask(w =>
			{
				if (self.IsDead)
					return;

				w.CreateActor(Info.Actor, new TypeDictionary
				{
					new LocationInit(spot),
					new OwnerInit(owner),
					new FactionInit(owner.Faction.InternalName)
				});
			});
		}

		static CPos? FreeCellNear(Actor self)
		{
			var world = self.World;
			for (var r = 1; r <= 2; r++)
			{
				for (var dx = -r; dx <= r; dx++)
				{
					for (var dy = -r; dy <= r; dy++)
					{
						var c = self.Location + new CVec(dx, dy);
						if (world.Map.Contains(c) && !world.ActorMap.AnyActorsAt(c))
							return c;
					}
				}
			}

			return null;
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using OpenRA.Mods.TGMC.Traits;

	[ScriptPropertyGroup("General")]
	public class MaturityProperties : ScriptActorProperties, Requires<MaturityInfo>
	{
		readonly Maturity maturity;

		public MaturityProperties(ScriptContext context, Actor self)
			: base(context, self)
		{
			maturity = self.Trait<Maturity>();
		}

		[Desc("The xeno's maturity tier: 0 young, then 1 mature, 2 elder, 3 ancient.")]
		public int MaturityTier => maturity.Tier;
	}
}
