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
		Forward
	}

	[Desc("A caste ability on a button of the command card (slot 1 or 2) and a hotkey: it can buff the unit for a while, hit what is in front of it or " +
		"nearest to it with a weapon, and bring up other units (the Carrier's huggers). It has a cooldown and, optionally, charges that refill over time.")]
	public class ActiveAbilityInfo : ConditionalTraitInfo
	{
		[Desc("Plasma the ability costs (see the Plasma trait). 0 for none.")]
		public readonly int PlasmaCost = 0;

		[Desc("Order name, unique among the unit's abilities.")]
		public readonly string OrderName = "Ability";

		[Desc("The command card button it takes: 1 or 2.")]
		public readonly int Slot = 1;

		[Desc("Short name on the button.")]
		public readonly string Label = "Ability";

		[Desc("Ticks before the ability can be used again.")]
		public readonly int Cooldown = 300;

		[Desc("Uses it holds. With more than one, each use takes one and a new one comes back every ChargeRegen ticks.")]
		public readonly int Charges = 1;

		public readonly int ChargeRegen = 0;

		[GrantedConditionReference]
		[Desc("Condition granted to the unit for Duration ticks (a buff). Leave empty for none.")]
		public readonly string Condition = null;

		public readonly int Duration = 0;

		[WeaponReference]
		[Desc("Weapon that hits the target (see Aim).")]
		public readonly string Weapon = null;

		public readonly AbilityAim Aim = AbilityAim.Nearest;
		public readonly WDist Range = new(1024);
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

		public UseAbilityActivity(ActiveAbility ability) { this.ability = ability; }

		public override bool Tick(Actor self)
		{
			if (IsCanceling)
				return true;

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
		public int ChargesLeft => charges;
		public bool Active => buffToken != Actor.InvalidConditionToken;
		public bool Ready => !IsTraitDisabled && cooldown == 0 && charges > 0 && (Info.PlasmaCost == 0 || (plasma ??= self.TraitOrDefault<Plasma>())?.Has(Info.PlasmaCost) != false);

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

			if (buffToken != Actor.InvalidConditionToken && --buffLeft <= 0)
				buffToken = self.RevokeCondition(buffToken);
		}

		void IResolveOrder.ResolveOrder(Actor self, Order order)
		{
			if (order.OrderString != Info.OrderName)
				return;

			if (order.Queued)
				self.QueueActivity(true, new UseAbilityActivity(this));
			else
				Use(self);
		}

		public bool Use(Actor self)
		{
			if (!Ready || self.IsDead)
				return false;

			var world = self.World;
			if (Info.TeleportDistance.Length > 0 && !Teleport(self))
				return false;

			if (Info.PlasmaCost > 0)
				(plasma ??= self.TraitOrDefault<Plasma>())?.Spend(Info.PlasmaCost);

			Target aim = Target.Invalid;
			if (Info.Weapon != null)
			{
				switch (Info.Aim)
				{
					case AbilityAim.Self:
						aim = Target.FromPos(self.CenterPosition);
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
				else
				{
					weapon.Impact(aim, args);
					if (Info.SelfDestruct)
						self.Kill(self);
				}
			}

			if (Info.Spawn.Length > 0)
				SpawnUnits(self);

			Fx.Sound(world, self.CenterPosition, Info.Sounds);
			Fx.Sprite(world, self.CenterPosition, Info.EffectImage, Info.EffectSequence, Info.Palette);
			return true;
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

		void SpawnUnits(Actor self)
		{
			var world = self.World;
			var toward = Nearest(self, Info.SpawnSeek)?.Location ?? self.Location;
			var cells = world.Map.FindTilesInCircle(self.Location, 2).OrderBy(c => (c - toward).LengthSquared).ToList();
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

		public void Spend(int amount) { value = System.Math.Max(0, value - amount); }

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

		[Desc("Use the ability in the given command card slot (1 or 2), as its button does. Returns false if it is not ready or has no target.")]
		public bool UseAbility(int slot)
		{
			var ability = Self.TraitsImplementing<ActiveAbility>().FirstOrDefault(a => a.Info.Slot == slot);
			return ability != null && ability.Use(Self);
		}

		[Desc("Queue the ability in the given slot behind the unit's current orders, as Shift plus its button does. Returns false if the unit has none in that slot.")]
		public bool QueueAbility(int slot)
		{
			var ability = Self.TraitsImplementing<ActiveAbility>().FirstOrDefault(a => a.Info.Slot == slot);
			if (ability == null)
				return false;

			Self.QueueActivity(true, new UseAbilityActivity(ability));
			return true;
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
