#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("The Alamo's hatch: the cell, relative to the footprint origin, where the squad steps out. Units trained at any marine building walk here while the Alamo stands.")]
	public class AlamoHatchInfo : TraitInfo
	{
		public readonly CVec Hatch = new(0, 9);

		public override object Create(ActorInitializer init) { return new AlamoHatch(); }
	}

	public class AlamoHatch { }

	[Desc("A marine production building: a unit it trains walks to the Alamo's hatch, while the Alamo stands. Without an Alamo the unit stays where it came out.")]
	public class RallyAtAlamoInfo : TraitInfo
	{
		public override object Create(ActorInitializer init) { return new RallyAtAlamo(); }
	}

	public class RallyAtAlamo : INotifyProduction
	{
		void INotifyProduction.UnitProduced(Actor self, Actor other, CPos exit)
		{
			var alamo = self.World.ActorsHavingTrait<AlamoHatch>()
				.FirstOrDefault(a => a.Owner == self.Owner && !a.IsDead && a.IsInWorld);
			if (alamo == null)
				return;

			var move = other.TraitOrDefault<IMove>();
			if (move == null)
				return;

			var hatch = alamo.Location + alamo.Info.TraitInfo<AlamoHatchInfo>().Hatch;
			other.QueueActivity(move.MoveTo(hatch, 1));
		}
	}
}
