#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using OpenRA.Effects;
using OpenRA.GameRules;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Projectiles;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Projectiles
{
	[Desc("A lobbed bullet (mortar, howitzer, rocket) that also whistles on its way down: the sound plays at the target spot shortly before the impact.")]
	public class ShellInfo : BulletInfo
	{
		[Desc("Sounds played at the target while the shell is in the air, one picked at random.")]
		public readonly string[] WhistleSounds = [];

		[Desc("How many ticks before the impact the whistle starts. A shell that flies for less than this whistles at once.")]
		public readonly int WhistleLead = 50;

		public override IProjectile Create(ProjectileArgs args)
		{
			var world = args.SourceActor.World;
			if (WhistleSounds.Length > 0)
			{
				var speed = Speed[0].Length;
				var distance = (args.PassiveTarget - args.Source).HorizontalLength;
				var flight = speed > 0 ? distance / speed : 0;
				world.AddFrameEndTask(w => w.Add(new Whistle(args.PassiveTarget, WhistleSounds, System.Math.Max(0, flight - WhistleLead))));
			}

			return base.Create(args);
		}
	}

	sealed class Whistle : IEffect
	{
		readonly WPos pos;
		readonly string[] sounds;
		int delay;

		public Whistle(WPos pos, string[] sounds, int delay)
		{
			this.pos = pos;
			this.sounds = sounds;
			this.delay = delay;
		}

		public void Tick(World world)
		{
			if (delay-- > 0)
				return;

			Fx.Sound(world, pos, sounds);
			world.AddFrameEndTask(w => w.Remove(this));
		}

		public System.Collections.Generic.IEnumerable<IRenderable> Render(WorldRenderer wr)
		{
			yield break;
		}
	}
}
