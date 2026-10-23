#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Activities;
using OpenRA.Effects;
using OpenRA.GameRules;
using OpenRA.Graphics;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Scripting;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	public enum AbilityAim
	{
		[Desc("The ability hits the unit's own cell.")]
		Self,
		[Desc("It hits the nearest enemy within Range, and is refused if there is none.")]
		Nearest,
		[Desc("It hits the ground ForwardDistance ahead of the unit.")]
		Forward,
		[Desc("The player clicks a spot within Range (the unit walks into reach first if it is further).")]
		Target,
		[Desc("The player clicks a unit within Range whose owner is in TargetRelationships.")]
		TargetActor
	}

	[Desc("A caste ability on a button of the command card (slot 1 or 2) and a hotkey: it can buff the unit for a while, hit what is in front of it or " +
		"nearest to it with a weapon, and bring up other units (the Carrier's huggers). It has a cooldown and, optionally, charges that refill over time.")]
	public class ActiveAbilityInfo : ConditionalTraitInfo
	{
		[Desc("Plasma the ability costs (see the Plasma trait). 0 for none.")]
		public readonly int PlasmaCost = 0;

		[Desc("Order name, unique among the unit's abilities.")]
		public readonly string OrderName = "Ability";

		[Desc("The command card slot it takes, 1 to 8 (the second and third rows, left to right).")]
		public readonly int Slot = 1;

		[Desc("Short name on the button.")]
		public readonly string Label = "Ability";

		[Desc("While the unit has this condition no ability of it can be used (a hunter's Silence). Not a lint reference: buildings never get it.")]
		public readonly string SilencedCondition = "silenced";

		[Desc("One line for the button's tooltip. The Label is used if empty.")]
		public readonly string Description = null;

		[Desc("Picture on the button, from the ability-icons collection (mod/build_icons.py). Defaults to the OrderName.")]
		public readonly string Icon = null;

		[Desc("Ticks before the ability can be used again.")]
		public readonly int Cooldown = 300;

		[Desc("Uses it holds. With more than one, each use takes one and a new one comes back every ChargeRegen ticks.")]
		public readonly int Charges = 1;

		public readonly int ChargeRegen = 0;

		[GrantedConditionReference]
		[Desc("Condition granted to the unit for Duration ticks (a buff). Leave empty for none.")]
		public readonly string Condition = null;

		public readonly int Duration = 0;

		[Desc("The unit dashes this far in a straight line: toward the clicked spot with Aim: Target, else straight ahead. It stops on the last " +
			"cell it can enter, and Weapon hits every enemy beside its path. 0 for no dash.")]
		public readonly WDist ChargeDistance = WDist.Zero;
		public readonly int ChargeTicks = 10;

		[Desc("How high the dash arcs: 0 for a run along the ground, about 512 for a pounce.")]
		public readonly WDist ChargeHeight = WDist.Zero;

		[Desc("Enemies the dash hits are thrown aside this far. 0 for none.")]
		public readonly WDist ChargeHitThrow = WDist.Zero;

		[Desc("Units within this range of the user get AuraCondition for AuraDuration ticks (a leader's order, a screech). 0 for none.")]
		public readonly WDist AuraRange = WDist.Zero;
		public readonly string AuraCondition = null;
		public readonly int AuraDuration = 250;
		public readonly PlayerRelationship AuraRelationships = PlayerRelationship.Ally;
		public readonly bool AuraIncludesSelf = true;

		[Desc("A word shouted over the user's head when it is used (\"MOVE!\").")]
		public readonly string Shout = null;
		public readonly Color ShoutColor = Color.FromArgb(255, 208, 64);

		[Desc("A ring of this colour spreads to AuraRange (or Range) when it is used. Unset for none.")]
		public readonly Color? Ring = null;

		[Desc("The button switches Condition on and off instead of timing it (a shell type, a cloak). Duration is not used.")]
		public readonly bool Toggle = false;

		[Desc("Toggles with the same Group on a unit are one choice: switching one on switches the others off, and one is always on.")]
		public readonly string Group = null;

		[Desc("A toggle that is on when the unit appears. A Group with none of these starts with its lowest slot on.")]
		public readonly bool StartOn = false;

		[WeaponReference]
		[Desc("Weapon that hits the target (see Aim).")]
		public readonly string Weapon = null;

		public readonly AbilityAim Aim = AbilityAim.Nearest;

		[Desc("Fire Weapon as a projectile from the unit (a grenade's arc, a shell's whistle) instead of hitting the target at once.")]
		public readonly bool Launch = false;
		public readonly WDist Range = new(1024);

		[Desc("Whose units Aim: TargetActor can pick: Enemy for an attack, Ally for a heal or a buff.")]
		public readonly PlayerRelationship TargetRelationships = PlayerRelationship.Enemy;
		public readonly WDist ForwardDistance = new(2048);

		[Desc("The unit blinks this far: next to the nearest enemy within it if there is one, else straight ahead (the wraith). 0 for no blink.")]
		public readonly WDist TeleportDistance = WDist.Zero;

		[Desc("Ticks between the use and the blast. The unit stands still and is seen to go off (the suicide vest's 2-second warcry).")]
		public readonly int FuseTicks = 0;

		[Desc("The unit dies in its own blast (the suicide vest).")]
		public readonly bool SelfDestruct = false;

		[ActorReference]
		[Desc("Units that appear next to the unit, one per entry.")]
		public readonly string[] Spawn = [];

		[Desc("Spawned units appear toward the nearest enemy within this range if there is one.")]
		public readonly WDist SpawnSeek = new(8 * 1024);

		[Desc("For the AI: it uses the ability when at least AiMinTargets enemy units are within AiRange. If AiWoundedPercent is above 0 it counts hurt " +
			"allies (below that share of their health) within AiRange instead, which is how it uses a heal.")]
		public readonly WDist AiRange = new(6 * 1024);
		public readonly int AiMinTargets = 1;
		public readonly int AiWoundedPercent = 0;

		public readonly string[] Sounds = [];
		public readonly string EffectImage = null;
		public readonly string EffectSequence = null;
		public readonly string Palette = "effect";

		public override object Create(ActorInitializer init) { return new ActiveAbility(init.Self, this); }
	}

	/// <summary>A queued ability use: fires when the unit reaches it, whether or not the use succeeds, then finishes.</summary>
	class UseAbilityActivity : Activity
	{
		readonly ActiveAbility ability;
		readonly Target target;

		public UseAbilityActivity(ActiveAbility ability, in Target target = default)
		{
			this.ability = ability;
			this.target = target;
		}

		public override bool Tick(Actor self)
		{
			if (IsCanceling)
				return true;

			// An aimed use whose target is gone (dead, or out of reach after the walk) is dropped and costs nothing.
			if (ability.IsAimed)
			{
				if (target.Type != TargetType.Invalid && ability.InReach(self, target))
					ability.Use(self, target);

				return true;
			}

			ability.Use(self);
			return true;
		}
	}

	public class ActiveAbility : ConditionalTrait<ActiveAbilityInfo>, IResolveOrder, ITick, ISelectionBar
	{
		readonly Actor self;
		int cooldown;
		int charges;
		int regen;
		int buffLeft;
		int buffToken = Actor.InvalidConditionToken;
		Plasma plasma;

		public ActiveAbility(Actor self, ActiveAbilityInfo info)
			: base(info)
		{
			this.self = self;
			charges = info.Charges;
		}

		public int CooldownRemaining => cooldown;
		public bool IsAimed => Info.Aim == AbilityAim.Target || Info.Aim == AbilityAim.TargetActor;
		public int ChargesLeft => charges;
		public bool Active => buffToken != Actor.InvalidConditionToken;
		bool silenced;

		public bool Ready => !IsTraitDisabled && !silenced && cooldown == 0 && charges > 0 && (Info.PlasmaCost == 0 || (plasma ??= self.TraitOrDefault<Plasma>())?.Has(Info.PlasmaCost) != false);

		float ISelectionBar.GetValue()
		{
			if (Info.Charges > 1)
				return charges < Info.Charges ? charges / (float)Info.Charges : 0f;

			return cooldown > 0 ? 1f - cooldown / (float)Math.Max(1, Info.Cooldown) : 0f;
		}

		Color ISelectionBar.GetColor() { return Color.FromArgb(255, 170, 60); }
		bool ISelectionBar.DisplayWhenEmpty => false;

		void ITick.Tick(Actor self)
		{
			if (cooldown > 0)
				cooldown--;

			if (Info.ChargeRegen > 0 && charges < Info.Charges && ++regen >= Info.ChargeRegen)
			{
				charges++;
				regen = 0;
			}

			if (!Info.Toggle && buffToken != Actor.InvalidConditionToken && --buffLeft <= 0)
				buffToken = self.RevokeCondition(buffToken);
		}

		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (order.OrderString != Info.OrderName)
				return;

			if (IsAimed)
			{
				UseAt(self, order.Target, order.Queued);
				return;
			}

			if (order.Queued)
				self.QueueActivity(true, new UseAbilityActivity(this));
			else
				Use(self);
		}

		public override IEnumerable<VariableObserver> GetVariableObservers()
		{
			foreach (var observer in base.GetVariableObservers())
				yield return observer;

			if (!string.IsNullOrEmpty(Info.SilencedCondition))
				yield return new VariableObserver((self, conditions) => silenced = conditions.TryGetValue(Info.SilencedCondition, out var n) && n > 0,
					[Info.SilencedCondition]);
		}

		protected override void Created(Actor self)
		{
			base.Created(self);
			if (!Info.Toggle || Info.Condition == null)
				return;

			var group = Info.Group == null ? [] : self.TraitsImplementing<ActiveAbility>().Where(a => a.Info.Toggle && a.Info.Group == Info.Group).ToList();
			var on = Info.StartOn || (group.Count > 0 && !group.Any(a => a.Info.StartOn) && group.MinBy(a => a.Info.Slot) == this);
			if (on)
				buffToken = self.GrantCondition(Info.Condition);
		}

		// A toggle: on grants Condition until switched off; in a Group, switching one on switches the others off and the one
		// that is on cannot be switched off by itself.
		bool Switch(Actor self)
		{
			if (Active)
			{
				if (Info.Group != null)
					return false;

				buffToken = self.RevokeCondition(buffToken);
				return true;
			}

			if (Info.Group != null)
				foreach (var other in self.TraitsImplementing<ActiveAbility>().Where(a => a != this && a.Info.Toggle && a.Info.Group == Info.Group && a.Active))
					other.buffToken = self.RevokeCondition(other.buffToken);

			buffToken = self.GrantCondition(Info.Condition);
			cooldown = Info.Cooldown;
			if (Info.PlasmaCost > 0)
				(plasma ??= self.TraitOrDefault<Plasma>())?.Spend(Info.PlasmaCost);

			Fx.Sound(self.World, self.CenterPosition, Info.Sounds);
			return true;
		}

		public bool InReach(Actor self, in Target target)
		{
			return (target.CenterPosition - self.CenterPosition).HorizontalLengthSquared <= Info.Range.LengthSquared;
		}

		/// <summary>Uses an aimed ability on a spot or unit: at once if it is in reach, else after walking into reach. False if it cannot.</summary>
		public bool UseAt(Actor self, in Target target, bool queued = false)
		{
			if (!IsAimed || !Ready || self.IsDead || target.Type == TargetType.Invalid)
				return false;

			if (Info.Aim == AbilityAim.TargetActor && (target.Type != TargetType.Actor
				|| !Info.TargetRelationships.HasRelationship(self.Owner.RelationshipWith(target.Actor.Owner))))
				return false;

			// A dash only takes its direction from the click; one aimed at the unit's own cell has none.
			if (Info.ChargeDistance.Length > 0 && self.World.Map.CellContaining(target.CenterPosition) == self.Location)
				return false;

			if (!queued && (InReach(self, target) || Info.ChargeDistance.Length > 0))
				return Use(self, target);

			var move = self.TraitOrDefault<IMove>();
			if (move == null)
				return false;

			if (!queued)
				self.CancelActivity();

			self.QueueActivity(move.MoveWithinRange(target, Info.Range, targetLineColor: Color.FromArgb(255, 208, 64)));
			self.QueueActivity(new UseAbilityActivity(this, target));
			return true;
		}

		public bool Use(Actor self) { return Use(self, Target.Invalid); }

		public bool Use(Actor self, in Target target)
		{
			if (!Ready || self.IsDead)
				return false;

			if (Info.Toggle)
				return Info.Condition != null && Switch(self);

			// An aimed ability needs its target: the button or Lua's UseAbilityAt/On gives it.
			if (IsAimed && target.Type == TargetType.Invalid)
				return false;

			var world = self.World;
			if (Info.TeleportDistance.Length > 0 && !Teleport(self))
				return false;

			Target aim = Target.Invalid;
			if (Info.Weapon != null || Info.ChargeDistance.Length > 0)
			{
				switch (Info.Aim)
				{
					case AbilityAim.Self:
						aim = Target.FromPos(self.CenterPosition);
						break;
					case AbilityAim.Target:
					case AbilityAim.TargetActor:
						aim = target;
						break;
					case AbilityAim.Forward:
						var facing = self.TraitOrDefault<IFacing>()?.Facing ?? WAngle.Zero;
						aim = Target.FromPos(self.CenterPosition + new WVec(0, -Info.ForwardDistance.Length, 0).Rotate(WRot.FromYaw(facing)));
						break;
					default:
						var victim = Nearest(self, Info.Range);
						if (victim == null)
							return false;

						aim = Target.FromActor(victim);
						break;
				}
			}

			// Paid only now that the ability has found what it hits: a refused use costs nothing.
			if (Info.PlasmaCost > 0)
				(plasma ??= self.TraitOrDefault<Plasma>())?.Spend(Info.PlasmaCost);

			if (Info.Charges > 1)
			{
				if (charges == Info.Charges)
					regen = 0;

				charges--;
			}

			cooldown = Info.Cooldown;

			if (Info.Condition != null && Info.Duration > 0)
			{
				if (buffToken == Actor.InvalidConditionToken)
					buffToken = self.GrantCondition(Info.Condition);

				buffLeft = Info.Duration;
			}

			if (Info.ChargeDistance.Length > 0)
			{
				Charge(self, aim);
				aim = Target.Invalid;
			}

			if (Info.Weapon != null && aim.Type != TargetType.Invalid)
			{
				var weapon = world.Map.Rules.Weapons[Info.Weapon.ToLowerInvariant()];
				var args = new WarheadArgs
				{
					Weapon = weapon,
					SourceActor = self,
					Source = self.CenterPosition,
					ImpactPosition = aim.CenterPosition,
					WeaponTarget = aim,
					DamageModifiers = self.TraitsImplementing<IFirepowerModifier>().Select(f => f.GetFirepowerModifier()).ToArray()
				};
				if (Info.FuseTicks > 0)
					world.AddFrameEndTask(w => w.Add(new Fuse(self, Info, weapon, aim.CenterPosition, Info.FuseTicks)));
				else if (Info.Launch && weapon.Projectile != null)
				{
					var facing = (aim.CenterPosition - self.CenterPosition).Yaw;
					var projectile = weapon.Projectile.Create(new ProjectileArgs
					{
						Weapon = weapon,
						Facing = facing,
						CurrentMuzzleFacing = () => facing,
						DamageModifiers = args.DamageModifiers,
						InaccuracyModifiers = [],
						RangeModifiers = [],
						Source = self.CenterPosition,
						CurrentSource = () => self.CenterPosition,
						SourceActor = self,
						PassiveTarget = aim.CenterPosition,
						GuidedTarget = aim
					});
					if (projectile != null)
						world.AddFrameEndTask(w => w.Add(projectile));

					if (weapon.Report != null && weapon.Report.Length > 0)
						Game.Sound.Play(SoundType.World, weapon.Report, world, self.CenterPosition);
				}
				else
				{
					weapon.Impact(aim, args);
					if (Info.SelfDestruct)
						self.Kill(self);
				}
			}

			if (Info.Spawn.Length > 0)
				SpawnUnits(self, IsAimed && target.Type != TargetType.Invalid ? self.World.Map.CellContaining(target.CenterPosition) : null);

			if (Info.AuraRange.Length > 0 && Info.AuraCondition != null)
				foreach (var a in world.FindActorsInCircle(self.CenterPosition, Info.AuraRange))
					if (!a.IsDead && a.IsInWorld && (a != self || Info.AuraIncludesSelf) && Info.AuraRelationships.HasRelationship(self.Owner.RelationshipWith(a.Owner)))
						a.TraitOrDefault<AuraReceiver>()?.Apply(a, Info.AuraCondition, Info.AuraDuration);

			Fx.Shout(world, self, Info.Shout, Info.ShoutColor);
			if (Info.Ring != null)
				Fx.Ring(world, self.CenterPosition, Info.AuraRange.Length > 0 ? Info.AuraRange : Info.Range, Info.Ring.Value);

			Fx.Sound(world, self.CenterPosition, Info.Sounds);
			Fx.Sprite(world, self.CenterPosition, Info.EffectImage, Info.EffectSequence, Info.Palette);
			return true;
		}

		// The dash: walk the cells toward the aim (or ahead), stop before the first one the unit cannot enter, hit the enemies beside the
		// path, then fly the unit there.
		void Charge(Actor self, in Target aim)
		{
			var mobile = self.TraitOrDefault<Mobile>();
			if (mobile == null || !self.IsInWorld)
				return;

			var world = self.World;
			var facing = self.TraitOrDefault<IFacing>()?.Facing ?? WAngle.Zero;
			var toward = aim.Type != TargetType.Invalid ? aim.CenterPosition - self.CenterPosition : new WVec(0, -1024, 0).Rotate(WRot.FromYaw(facing));
			if (toward.HorizontalLengthSquared == 0)
				return;

			var step = new WVec(toward.X, toward.Y, 0) * 1024 / toward.HorizontalLength;
			var landing = self.Location;
			var path = new List<WPos>();
			for (var i = 1; i <= Info.ChargeDistance.Length / 1024; i++)
			{
				var pos = self.CenterPosition + step * i;
				var cell = world.Map.CellContaining(pos);
				if (!world.Map.Contains(cell) || !mobile.CanEnterCell(cell, self))
					break;

				landing = cell;
				path.Add(pos);
			}

			if (Info.Weapon != null)
			{
				var weapon = world.Map.Rules.Weapons[Info.Weapon.ToLowerInvariant()];
				var hit = path.SelectMany(p => world.FindActorsInCircle(p, new WDist(1280))).Distinct()
					.Where(a => a != self && !a.IsDead && self.Owner.RelationshipWith(a.Owner) == PlayerRelationship.Enemy).ToList();
				foreach (var victim in hit)
				{
					weapon.Impact(Target.FromActor(victim), new WarheadArgs
					{
						Weapon = weapon,
						SourceActor = self,
						Source = self.CenterPosition,
						ImpactPosition = victim.CenterPosition,
						WeaponTarget = Target.FromActor(victim),
						DamageModifiers = self.TraitsImplementing<IFirepowerModifier>().Select(f => f.GetFirepowerModifier()).ToArray()
					});
					if (Info.ChargeHitThrow.Length > 0 && !victim.IsDead)
						Warheads.KnockbackWarhead.Throw(victim, self, self.CenterPosition, Info.ChargeHitThrow, 12, new WDist(512), 0, 0, default);
				}
			}

			if (landing == self.Location)
				return;

			self.CancelActivity();
			self.QueueActivity(new Warheads.Thrown(self, mobile, landing, Info.ChargeTicks, Info.ChargeHeight.Length, 0, self, default));
		}

		bool Teleport(Actor self)
		{
			var map = self.World.Map;
			var body = self.TraitOrDefault<IPositionable>();
			if (body == null || !self.IsInWorld)
				return false;

			var foe = Nearest(self, Info.TeleportDistance);
			IEnumerable<CPos> options;
			if (foe != null)
				options = map.FindTilesInCircle(foe.Location, 2).Where(c => c != foe.Location).OrderBy(c => (c - self.Location).LengthSquared);
			else
			{
				var facing = self.TraitOrDefault<IFacing>()?.Facing ?? WAngle.Zero;
				var ahead = new WVec(0, -1024, 0).Rotate(WRot.FromYaw(facing));
				options = Enumerable.Range(1, Info.TeleportDistance.Length / 1024).Reverse().Select(i => map.CellContaining(self.CenterPosition + ahead * i));
			}

			var cell = options.FirstOrDefault(c => c != self.Location && map.Contains(c) && body.CanEnterCell(c));
			if (cell == default)
				return false;

			Fx.Sprite(self.World, self.CenterPosition, Info.EffectImage, Info.EffectSequence, Info.Palette);
			self.CancelActivity();
			body.SetPosition(self, cell);
			return true;
		}

		static Actor Nearest(Actor self, WDist range)
		{
			return self.World.FindActorsInCircle(self.CenterPosition, range)
				.Where(a => !a.IsDead && a.IsInWorld && self.Owner.RelationshipWith(a.Owner) == PlayerRelationship.Enemy && a.Info.HasTraitInfo<MobileInfo>())
				.MinByOrDefault(a => (a.CenterPosition - self.CenterPosition).LengthSquared);
		}

		// Spawned units go next to the unit, toward the nearest enemy; an aimed spawn (a barricade) goes on the clicked cell.
		void SpawnUnits(Actor self, CPos? at)
		{
			var world = self.World;
			var toward = at ?? Nearest(self, Info.SpawnSeek)?.Location ?? self.Location;
			var cells = world.Map.FindTilesInCircle(at ?? self.Location, 2).OrderBy(c => (c - toward).LengthSquared).ToList();
			var used = new HashSet<CPos>();
			var owner = self.Owner;
			foreach (var type in Info.Spawn)
			{
				var actorInfo = world.Map.Rules.Actors[type];
				var mobile = actorInfo.TraitInfoOrDefault<MobileInfo>();
				var building = actorInfo.TraitInfoOrDefault<BuildingInfo>();
				// A structure (an egg) goes where it could be placed, ignoring the build area; a unit where it can stand.
				var cell = cells.FirstOrDefault(c => c != self.Location && !used.Contains(c) && world.Map.Contains(c)
					&& (mobile != null ? mobile.CanEnterCell(world, null, c) : building == null || world.CanPlaceBuilding(c, actorInfo, building, null)));
				if (cell == default)
					continue;

				used.Add(cell);
				var spawn = type;
				world.AddFrameEndTask(w => w.CreateActor(spawn, new TypeDictionary
				{
					new LocationInit(cell),
					new OwnerInit(owner),
					new FactionInit(owner.Faction.InternalName)
				}));
			}
		}
	}
}

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Lets a unit take the timed buffs that abilities' auras hand out (leader orders, screeches). A buff given again while it runs " +
		"is refreshed, never doubled.")]
	public class AuraReceiverInfo : TraitInfo
	{
		[GrantedConditionReference]
		[Desc("The aura conditions this unit can take.")]
		public readonly string[] Conditions = [];

		public override object Create(ActorInitializer init) { return new AuraReceiver(this); }
	}

	public class AuraReceiver : ITick
	{
		readonly AuraReceiverInfo info;
		readonly Dictionary<string, (int Token, int Left)> running = [];

		public AuraReceiver(AuraReceiverInfo info) { this.info = info; }

		public void Apply(Actor self, string condition, int duration)
		{
			if (!info.Conditions.Contains(condition))
				return;

			running[condition] = running.TryGetValue(condition, out var on)
				? (on.Token, Math.Max(on.Left, duration))
				: (self.GrantCondition(condition), duration);
		}

		public bool Has(string condition) { return running.ContainsKey(condition); }

		void ITick.Tick(Actor self)
		{
			foreach (var condition in running.Keys.ToList())
			{
				var (token, left) = running[condition];
				if (--left > 0)
					running[condition] = (token, left);
				else
				{
					self.RevokeCondition(token);
					running.Remove(condition);
				}
			}
		}
	}

	[ScriptPropertyGroup("Abilities")]
	public class AuraReceiverProperties : ScriptActorProperties, Requires<AuraReceiverInfo>
	{
		public AuraReceiverProperties(ScriptContext context, Actor self)
			: base(context, self) { }

		[Desc("True while an aura buff (an order, a screech) with this condition is on the unit.")]
		public bool HasAuraCondition(string condition) { return Self.Trait<AuraReceiver>().Has(condition); }

		[Desc("How many times this aura buff is on the unit: 0 or 1, since a second one only refreshes the first.")]
		public int AuraStacks(string condition) { return Self.Trait<AuraReceiver>().Has(condition) ? 1 : 0; }
	}

	[ScriptPropertyGroup("Abilities")]
	public class PlasmaProperties : ScriptActorProperties, Requires<PlasmaInfo>
	{
		public PlasmaProperties(ScriptContext context, Actor self)
			: base(context, self) { }

		[Desc("The plasma this xeno has now.")]
		public int Plasma => Self.Trait<Plasma>().Value;
	}

	[Desc("A xeno's plasma: the fuel of its abilities (ActiveAbility.PlasmaCost). It builds up slowly, and faster while the xeno stands on weeds. A purple bar shows it.")]
	public class PlasmaInfo : TraitInfo
	{
		public readonly int Max = 100;

		[Desc("Ticks to gain one point, and ticks to gain one while on weeds.")]
		public readonly int Regen = 8;
		public readonly int WeedRegen = 3;

		[Desc("Actor types that count as weeds.")]
		public readonly string[] Weeds = ["weeds", "weed-node", "forward-hive", "resin-silo"];

		[Desc("Starts with this share of the maximum, in percent.")]
		public readonly int StartPercent = 60;

		public override object Create(ActorInitializer init) { return new Plasma(init.Self, this); }
	}

	public class Plasma : ITick, ISelectionBar
	{
		readonly Actor self;
		readonly PlasmaInfo info;
		int value;
		int wait;

		public Plasma(Actor self, PlasmaInfo info)
		{
			this.self = self;
			this.info = info;
			value = info.Max * info.StartPercent / 100;
		}

		public int Value => value;
		public bool Has(int amount) { return value >= amount; }

		public void Spend(int amount) { value = System.Math.Clamp(value - amount, 0, info.Max); }

		void ITick.Tick(Actor self)
		{
			if (value >= info.Max)
				return;

			var onWeeds = self.World.ActorMap.GetActorsAt(self.Location).Any(a => info.Weeds.Contains(a.Info.Name));
			if (++wait >= (onWeeds ? info.WeedRegen : info.Regen))
			{
				wait = 0;
				value++;
			}
		}

		float ISelectionBar.GetValue() { return value / (float)info.Max; }
		Color ISelectionBar.GetColor() { return Color.FromArgb(190, 90, 255); }
		bool ISelectionBar.DisplayWhenEmpty => true;
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using OpenRA.Mods.TGMC.Traits;

	[ScriptPropertyGroup("Combat")]
	public class ActiveAbilityProperties : ScriptActorProperties, Requires<ActiveAbilityInfo>
	{
		public ActiveAbilityProperties(ScriptContext context, Actor self)
			: base(context, self) { }

		// The ability in a slot; with two on one slot (the boiler's bombards, one per glob type) the one switched on.
		ActiveAbility InSlot(int slot)
		{
			return Self.TraitsImplementing<ActiveAbility>().Where(a => a.Info.Slot == slot).OrderBy(a => a.IsTraitDisabled).FirstOrDefault();
		}

		[Desc("Use the ability in the given command card slot (1 to 8), as its button does. Returns false if it is not ready or has no target.")]
		public bool UseAbility(int slot)
		{
			var ability = InSlot(slot);
			return ability != null && ability.Use(Self);
		}

		[Desc("Queue the ability in the given slot behind the unit's current orders, as Shift plus its button does. Returns false if the unit has none in that slot.")]
		public bool QueueAbility(int slot)
		{
			var ability = InSlot(slot);
			if (ability == null)
				return false;

			Self.QueueActivity(true, new UseAbilityActivity(ability));
			return true;
		}

		[Desc("Use the aimed ability in the given slot on a cell, as a click does: the unit walks into reach first if it must. False if it cannot.")]
		public bool UseAbilityAt(int slot, CPos cell)
		{
			var ability = InSlot(slot);
			return ability != null && ability.UseAt(Self, Target.FromCell(Self.World, cell));
		}

		[Desc("Use the aimed ability in the given slot on a unit, as a click does. False if it cannot.")]
		public bool UseAbilityOn(int slot, Actor target)
		{
			var ability = InSlot(slot);
			return ability != null && ability.UseAt(Self, Target.FromActor(target));
		}

		[Desc("How the ability in the given slot is aimed: Self, Nearest, Forward, Target or TargetActor. Empty if there is none.")]
		public string AbilityAim(int slot)
		{
			return InSlot(slot)?.Info.Aim.ToString() ?? "";
		}

		[Desc("True if the ability in the given slot is on: a toggle switched on, or a buff still running.")]
		public bool AbilityActive(int slot)
		{
			return Self.TraitsImplementing<ActiveAbility>().Any(a => a.Info.Slot == slot && a.Active);
		}

		[Desc("True if the ability in the given slot is ready to use now.")]
		public bool AbilityReady(int slot)
		{
			return Self.TraitsImplementing<ActiveAbility>().Any(a => a.Info.Slot == slot && a.Ready);
		}
	}
}

namespace OpenRA.Mods.TGMC.Traits
{
	/// <summary>A fuse: the blast goes off after the ticks run out, wherever the unit is then, and the unit dies in it if it is meant to.</summary>
	sealed class Fuse : IEffect
	{
		readonly Actor source;
		readonly ActiveAbilityInfo info;
		readonly WeaponInfo weapon;
		readonly WPos pos;
		int ticks;

		public Fuse(Actor source, ActiveAbilityInfo info, WeaponInfo weapon, WPos pos, int ticks)
		{
			this.source = source;
			this.info = info;
			this.weapon = weapon;
			this.pos = pos;
			ticks = info.FuseTicks;
		}

		void IEffect.Tick(World world)
		{
			if (--ticks > 0)
				return;

			var at = source.IsDead ? pos : source.CenterPosition;
			var args = new WarheadArgs
			{
				Weapon = weapon,
				SourceActor = source,
				Source = at,
				DamageModifiers = []
			};
			weapon.Impact(Target.FromPos(at), args);
			if (info.SelfDestruct && !source.IsDead)
				source.Kill(source);

			world.AddFrameEndTask(w => w.Remove(this));
		}

		IEnumerable<IRenderable> IEffect.Render(WorldRenderer wr) { yield break; }
	}
}
