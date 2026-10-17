#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("The actor is removed after this many ticks: a decoy or a sensor ping that a weapon spawned and nobody has to clean up.")]
	public class ExpiresInfo : TraitInfo
	{
		[Desc("Ticks the actor lives.")]
		public readonly int Ticks = 750;

		public override object Create(ActorInitializer init) { return new Expires(this); }
	}

	public class Expires : ITick
	{
		readonly int ticks;
		int left;

		public Expires(ExpiresInfo info)
		{
			ticks = info.Ticks;
			left = info.Ticks;
		}

		void ITick.Tick(Actor self)
		{
			if (--left <= 0 && !self.IsDead)
				self.Dispose();
		}
	}
}
