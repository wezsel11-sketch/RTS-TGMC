#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Collections.Generic;
using System.Linq;
using OpenRA.Effects;
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

		[Desc("Ticks the pod takes to fall, and the height it starts from.")]
		public readonly int FallTicks = 45;
		public readonly WDist Height = new(14 * 1024);

		[Desc("Ticks after landing before the door opens and the marines step out.")]
		public readonly int OpenDelay = 20;

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
			self.World.AddFrameEndTask(w => w.Add(new PodDrop(self.Owner, info, order.Target.CenterPosition)));
		}
	}

	sealed class PodDrop : IEffect
	{
		readonly Player owner;
		readonly DropPodPowerInfo info;
		readonly WPos target;
		readonly World world;
		SpriteEffect falling;
		int tick;
		bool landed;

		public PodDrop(Player owner, DropPodPowerInfo info, WPos target)
		{
			this.owner = owner;
			this.info = info;
			this.target = target;
			world = owner.World;
			Fx.Sound(world, target, info.FallSounds);
			falling = new SpriteEffect(Where, () => WAngle.Zero, world, info.Image, info.FallSequence, info.Palette);
			world.Add(falling);
		}

		WPos Where()
		{
			var left = Math.Max(0, info.FallTicks - tick);
			return target + new WVec(0, 0, info.Height.Length * left * left / (info.FallTicks * info.FallTicks));
		}

		void IEffect.Tick(World w)
		{
			tick++;
			if (!landed && tick >= info.FallTicks)
			{
				landed = true;
				world.Remove(falling);
				world.Add(new SpriteEffect(target, world, info.Image, info.LandedSequence, info.Palette));
				Fx.Sound(world, target, info.LandSounds);
				world.WorldActor.TraitOrDefault<ScreenShaker>()?.AddEffect(14, target, 4);
				Fx.Sprite(world, target, "fx-dust-tile", "dust", "effect");
			}

			if (landed && tick >= info.FallTicks + info.OpenDelay)
			{
				Release();
				world.AddFrameEndTask(x => x.Remove(this));
			}
		}

		void Release()
		{
			var centre = world.Map.CellContaining(target);
			var cells = world.Map.FindTilesInCircle(centre, info.Radius + 1).OrderBy(c => (c - centre).LengthSquared).ToList();
			var used = new HashSet<CPos>();
			foreach (var type in info.Actors)
			{
				var mobile = world.Map.Rules.Actors[type].TraitInfoOrDefault<MobileInfo>();
				var cell = cells.FirstOrDefault(c => !used.Contains(c) && (mobile == null || mobile.CanEnterCell(world, null, c)));
				if (cell == default)
					continue;

				used.Add(cell);
				var spawn = type;
				world.AddFrameEndTask(x => x.CreateActor(spawn, new TypeDictionary
				{
					new LocationInit(cell),
					new OwnerInit(owner),
					new FactionInit(owner.Faction.InternalName)
				}));
			}
		}

		System.Collections.Generic.IEnumerable<IRenderable> IEffect.Render(WorldRenderer wr) { yield break; }
	}
}
