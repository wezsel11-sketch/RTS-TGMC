#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose warheads this file extends.
#endregion

using System.Linq;
using OpenRA.GameRules;
using OpenRA.Mods.Common.Warheads;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Warheads
{
	[Desc("Puts an actor on the ground at the impact and along the line back toward the firer, one per cell. For the flamer, " +
		"whose flames keep burning on the ground. A cell that already holds one is skipped.")]
	public class SpawnActorWarhead : Warhead
	{
		[ActorReference]
		[Desc("The actor to place (a short-lived one that damages what stands on it).")]
		public readonly string Actor = null;

		[Desc("How many cells back from the impact toward the firer get one as well.")]
		public readonly int TrailCells = 0;

		public override void DoImpact(in Target target, WarheadArgs args)
		{
			var firedBy = args.SourceActor;
			if (firedBy == null || Actor == null)
				return;

			// The target can be gone by the time an instant weapon lands (a marked enemy that just died): nothing to spawn on.
			if (target.Type == TargetType.Invalid)
				return;

			var world = firedBy.World;
			var impact = target.CenterPosition;
			var from = args.Source ?? firedBy.CenterPosition;
			var map = world.Map;
			var end = map.CellContaining(impact);
			var cells = new System.Collections.Generic.List<CPos> { end };

			// Walk from the impact back toward the firer, a cell at a time.
			var back = from - impact;
			if (TrailCells > 0 && back.HorizontalLengthSquared > 0)
			{
				var step = new WVec(back.X, back.Y, 0) * 1024 / back.HorizontalLength;
				for (var i = 1; i <= TrailCells; i++)
				{
					var c = map.CellContaining(impact + step * i);
					if (c != map.CellContaining(from) && !cells.Contains(c))
						cells.Add(c);
				}
			}

			world.AddFrameEndTask(w =>
			{
				foreach (var cell in cells)
				{
					if (!map.Contains(cell) || w.ActorMap.GetActorsAt(cell).Any(a => a.Info.Name == Actor))
						continue;

					w.CreateActor(Actor, new TypeDictionary
					{
						new OwnerInit(firedBy.Owner),
						new LocationInit(cell),
					});
				}
			});
		}
	}
}
