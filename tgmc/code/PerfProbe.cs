#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Linq;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.World)]
	[Desc("Debug aid for test maps, not for play: prints how many effects (by type) and actors the world holds every Interval ticks, to find " +
		"what piles up when a long match slows down.")]
	public class PerfProbeInfo : TraitInfo
	{
		public readonly int Interval = 250;

		public override object Create(ActorInitializer init) { return new PerfProbe(this); }
	}

	public class PerfProbe : ITick
	{
		readonly PerfProbeInfo info;

		public PerfProbe(PerfProbeInfo info) { this.info = info; }

		void ITick.Tick(Actor self)
		{
			var world = self.World;
			if (world.WorldTick % info.Interval != 0)
				return;

			var effects = world.Effects.GroupBy(e => e.GetType().Name).OrderByDescending(g => g.Count()).Take(8).Select(g => $"{g.Key}={g.Count()}");
			Console.WriteLine($"PERFPROBE t={world.WorldTick} actors={world.Actors.Count()} effects={world.Effects.Count()} {string.Join(" ", effects)}");
		}
	}
}
