#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Leaves a gas cloud behind as the unit walks: a cloud every few cells, so the ground it crossed stays poisoned for a while (the defiler).")]
	public class GasTrailInfo : TraitInfo, Requires<MobileInfo>
	{
		[Desc("The gas cloud actor left on the ground.")]
		public readonly string Actor = "gas-cloud";

		[Desc("Ticks between two clouds while walking.")]
		public readonly int Interval = 30;

		public override object Create(ActorInitializer init) { return new GasTrail(init.Self, this); }
	}

	public class GasTrail : ITick
	{
		readonly GasTrailInfo info;
		CPos last;
		int wait;

		public GasTrail(Actor self, GasTrailInfo info)
		{
			this.info = info;
			last = self.Location;
		}

		void ITick.Tick(Actor self)
		{
			if (wait > 0)
				wait--;

			var mobile = self.TraitOrDefault<Mobile>();
			if (mobile == null || self.IsDead || !self.IsInWorld)
				return;

			if (mobile.IsMovingBetweenCells && wait == 0 && self.Location != last)
			{
				last = self.Location;
				wait = info.Interval;
				var cell = self.Location;
				self.World.AddFrameEndTask(w => w.CreateActor(info.Actor, new TypeDictionary
				{
					new LocationInit(cell),
					new OwnerInit(self.Owner)
				}));
			}
		}
	}
}
