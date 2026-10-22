#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Leaves a gas cloud behind as the unit walks: a cloud every few cells, so the ground it crossed stays poisoned for a while (the defiler).")]
	public class GasTrailInfo : ConditionalTraitInfo, Requires<MobileInfo>
	{
		[Desc("The gas cloud actor left on the ground.")]
		public readonly string Actor = "gas-cloud";

		[Desc("Ticks between two clouds while walking.")]
		public readonly int Interval = 30;

		[Desc("Cells around the unit that get a cloud each time, as a disc (0 is just the cell it stands in). A cell that already has one is skipped.")]
		public readonly int Radius = 0;

		[Desc("Only cells whose X and Y are both multiples of this get a cloud, so a disc is not packed with overlapping clouds (a cloud already reaches about 2 cells).")]
		public readonly int Spacing = 1;

		public override object Create(ActorInitializer init) { return new GasTrail(init.Self, this); }
	}

	public class GasTrail : ConditionalTrait<GasTrailInfo>, ITick
	{
		readonly GasTrailInfo info;
		CPos last;
		int wait;

		public GasTrail(Actor self, GasTrailInfo info)
			: base(info)
		{
			this.info = info;
			last = self.Location;
		}

		void ITick.Tick(Actor self)
		{
			if (wait > 0)
				wait--;

			var mobile = self.TraitOrDefault<Mobile>();
			if (IsTraitDisabled || mobile == null || self.IsDead || !self.IsInWorld)
				return;

			if (mobile.IsMovingBetweenCells && wait == 0 && self.Location != last)
			{
				last = self.Location;
				wait = info.Interval;
				var cells = info.Radius > 0 ? self.World.Map.FindTilesInCircle(self.Location, info.Radius).Where(c => c.X % info.Spacing == 0 && c.Y % info.Spacing == 0).ToList() : [self.Location];
				self.World.AddFrameEndTask(w =>
				{
					foreach (var cell in cells)
					{
						if (info.Radius > 0 && w.ActorMap.GetActorsAt(cell).Any(a => a.Info.Name == info.Actor))
							continue;

						w.CreateActor(info.Actor, new TypeDictionary
						{
							new LocationInit(cell),
							new OwnerInit(self.Owner)
						});
					}
				});
			}
		}
	}
}
