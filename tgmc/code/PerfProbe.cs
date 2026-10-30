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

	[TraitLocation(SystemActors.World)]
	[Desc("Test aid: with TGMC_FAST=1 in the environment the world ticks as fast as the CPU allows and nothing is drawn, so headless " +
		"scenario and balance runs finish in a fraction of real time. Without the variable it does nothing. Never set it for play or screenshots.")]
	public class HeadlessTestSpeedInfo : TraitInfo
	{
		public override object Create(ActorInitializer init) { return new HeadlessTestSpeed(); }
	}

	public class HeadlessTestSpeed : IWorldLoaded, ITick
	{
		const System.Reflection.BindingFlags Hidden = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
		static readonly bool Enabled = Environment.GetEnvironmentVariable("TGMC_FAST") == "1";
		object window;
		System.Reflection.PropertyInfo suspended;
		Network.OrderManager orderManager;

		// shortcut: reaches two engine internals by reflection, the world's OrderManager (its tick scale is the server's lag adjustment; the
		// world's own Timestep is fixed by the game speed) and the SDL window's IsSuspended flag (the engine's "minimised" path: logic ticks,
		// nothing is drawn). Replace it if OpenRA gets a real headless switch.
		void IWorldLoaded.WorldLoaded(World w, Graphics.WorldRenderer wr)
		{
			if (!Enabled || w.Type != WorldType.Regular)
				return;

			orderManager = typeof(World).GetField("OrderManager", Hidden)?.GetValue(w) as Network.OrderManager;
			window = typeof(Renderer).GetProperty("Window", Hidden)?.GetValue(Game.Renderer);
			suspended = window?.GetType().GetProperty("IsSuspended");
			Apply();
			Console.WriteLine($"TGMC_FAST: tick scale {(orderManager != null ? "0.01" : "unchanged (not found)")}, drawing {(suspended != null ? "off" : "on (window flag not found)")}");
		}

		void Apply()
		{
			orderManager?.ReceiveTickScale(0.01f);
			suspended?.SetValue(window, true);
		}

		// A window event (shown, exposed) can clear the flag again, and the server can send a new tick scale.
		void ITick.Tick(Actor self)
		{
			if (Enabled && self.World.WorldTick % 25 == 0)
				Apply();
		}
	}
}
