#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Effects;
using OpenRA.GameRules;
using OpenRA.Graphics;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Effects;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Marine support power: a drop pod falls from orbit onto the spot you pick, shakes the ground as it lands, and its door opens on the marines inside.")]
	public class DropPodPowerInfo : SupportPowerInfo
	{
		[ActorReference]
		[Desc("The marines in the pod. They belong to the player who calls it.")]
		public readonly string[] Actors = [];

		[Desc("Cells around the landing spot they step out onto.")]
		public readonly int Radius = 2;

		[Desc("Radius of the circle shown under the cursor while aiming: the area the pod serves.")]
		public readonly WDist MarkerRadius = new(1536);

		public readonly Color MarkerColor = Color.FromArgb(170, 90, 200, 255);

		[Desc("Ticks the pod takes to fall, and the height it starts from.")]
		public readonly int FallTicks = 30;
		public readonly WDist Height = new(14 * 1024);

		[Desc("Ticks after landing before the door opens and the marines step out.")]
		public readonly int OpenDelay = 20;

		[Desc("Each actor comes in a pod of its own. Ticks between one pod and the next landing.")]
		public readonly int PodInterval = 6;

		[Desc("The pod hits the ground hard: this weapon goes off where it lands (it hurts whatever is under it).")]
		public readonly string LandWeapon = "TGMCPodImpact";

		[Desc("Ticks the empty pod stays on the ground before it is gone (750 is 30 seconds).")]
		public readonly int WreckTicks = 750;

		public readonly string Image = "droppod";
		public readonly string FallSequence = "fall";
		public readonly string LandedSequence = "landed";
		public readonly string Palette = "effect";

		public readonly string[] FallSounds = [];
		public readonly string[] LandSounds = [];

		public override object Create(ActorInitializer init) { return new DropPodPower(init.Self, this); }
	}

	public class DropPodPower : SupportPower
	{
		readonly DropPodPowerInfo info;

		public DropPodPower(Actor self, DropPodPowerInfo info)
			: base(self, info)
		{
			this.info = info;
		}

		public override void Activate(Actor self, Order order, SupportPowerManager manager)
		{
			base.Activate(self, order, manager);
			Drop(self, order.Target.CenterPosition);
		}

		public override void SelectTarget(Actor self, string order, SupportPowerManager manager)
		{
			self.World.OrderGenerator = new AreaTargetGenerator(order, manager, info.Cursor, info.BlockedCursor, info.MarkerRadius, info.MarkerColor);
		}

		public bool Carries(string actor) { return info.Actors.Contains(actor); }

		public void Drop(Actor self, WPos target)
		{
			// One pod for each actor, each on a cell of its own around the spot, one after the other.
			var world = self.World;
			var map = world.Map;
			var centre = map.CellContaining(target);
			var cells = map.FindTilesInCircle(centre, info.Radius + 1).OrderBy(c => (c - centre).LengthSquared).ToList();
			var used = new List<CPos>();
			for (var i = 0; i < info.Actors.Length; i++)
			{
				var type = info.Actors[i];
				var cell = cells.FirstOrDefault(c => !used.Contains(c) && used.All(u => Math.Max(Math.Abs(u.X - c.X), Math.Abs(u.Y - c.Y)) > 1));
				if (cell == default)
					cell = cells.FirstOrDefault(c => !used.Contains(c));
				if (cell == default)
					cell = centre;

				used.Add(cell);
				var spot = i == 0 && info.Actors.Length == 1 ? target : map.CenterOfCell(cell);
				var delay = i * info.PodInterval;
				world.AddFrameEndTask(w => w.Add(new PodDrop(self.Owner, info, type, spot, delay)));
			}
		}
	}

	sealed class PodDrop : IEffect
	{
		readonly Player owner;
		readonly DropPodPowerInfo info;
		readonly string type;
		readonly WPos target;
		readonly World world;
		SpriteEffect falling;
		SpriteEffect wreck;
		int wait;
		int tick;
		bool landed;
		bool released;

		public PodDrop(Player owner, DropPodPowerInfo info, string type, WPos target, int delay)
		{
			this.owner = owner;
			this.info = info;
			this.type = type;
			this.target = target;
			wait = delay;
			world = owner.World;
		}

		WPos Where()
		{
			var left = Math.Max(0, info.FallTicks - tick);
			return target + new WVec(0, 0, info.Height.Length * left * left / (info.FallTicks * info.FallTicks));
		}

		void IEffect.Tick(World w)
		{
			if (wait > 0)
			{
				wait--;
				return;
			}

			if (falling == null)
			{
				Fx.Sound(world, target, info.FallSounds);
				falling = new SpriteEffect(Where, () => WAngle.Zero, world, info.Image, info.FallSequence, info.Palette);
				world.AddFrameEndTask(x => x.Add(falling));
			}

			tick++;
			if (!landed && tick >= info.FallTicks)
			{
				landed = true;
				world.AddFrameEndTask(x =>
				{
					x.Remove(falling);
					wreck = new SpriteEffect(target, x, info.Image, info.LandedSequence, info.Palette);
					x.Add(wreck);
					Fx.Sound(x, target, info.LandSounds);
					Fx.Sprite(x, target, "fx-dust-tile", "dust", "effect");
					if (info.LandWeapon != null && x.Map.Rules.Weapons.TryGetValue(info.LandWeapon.ToLowerInvariant(), out var weapon))
					{
						var args = new WarheadArgs
						{
							Weapon = weapon,
							SourceActor = owner.PlayerActor,
							Source = target,
							ImpactPosition = target,
							WeaponTarget = Target.FromPos(target),
							DamageModifiers = []
						};
						weapon.Impact(Target.FromPos(target), args);
					}
				});
			}

			if (landed && !released && tick >= info.FallTicks + info.OpenDelay)
			{
				released = true;
				Release();
			}

			if (landed && tick >= info.FallTicks + info.WreckTicks)
			{
				world.AddFrameEndTask(x =>
				{
					if (wreck != null)
						x.Remove(wreck);

					x.Remove(this);
				});
			}
		}

		void Release()
		{
			var centre = world.Map.CellContaining(target);
			var mobile = world.Map.Rules.Actors[type].TraitInfoOrDefault<MobileInfo>();
			var cell = world.Map.FindTilesInCircle(centre, 3)
				.OrderBy(c => (c - centre).LengthSquared)
				.FirstOrDefault(c => mobile == null || mobile.CanEnterCell(world, null, c));
			if (cell == default)
				return;

			world.AddFrameEndTask(x => x.CreateActor(type, new TypeDictionary
			{
				new LocationInit(cell),
				new OwnerInit(owner),
				new FactionInit(owner.Faction.InternalName)
			}));
		}

		System.Collections.Generic.IEnumerable<IRenderable> IEffect.Render(WorldRenderer wr) { yield break; }
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using Eluant;
	using OpenRA.Scripting;
	using OpenRA.Mods.TGMC.Traits;

	[ScriptPropertyGroup("Support Powers")]
	public class DropPodProperties : ScriptActorProperties, Requires<DropPodPowerInfo>
	{
		public DropPodProperties(ScriptContext context, Actor self)
			: base(context, self) { }

		[Desc("Drop the pod of this support power that carries the actor type (for example \"mortar-emplacement\") on the cell, at once, charged or not.")]
		public void CallDropPod(CPos target, string actor)
		{
			foreach (var power in Self.TraitsImplementing<DropPodPower>())
			{
				if (power.Carries(actor))
				{
					power.Drop(Self, Self.World.Map.CenterOfCell(target));
					return;
				}
			}

			throw new LuaException($"The actor has no drop pod carrying '{actor}'.");
		}
	}
}
