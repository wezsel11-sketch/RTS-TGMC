#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using OpenRA.Mods.Common.Effects;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("When the unit dies of one of GibTypes (an explosion), body parts fly out of it, land a few cells away with a splash of blood and lie there for a long time.")]
	public class ThrowsGibsInfo : TraitInfo
	{
		public readonly string Image = "fx-gibs";

		[Desc("Sequences of Image to throw: body parts, one of them per piece, picked at random.")]
		public readonly string[] Parts = [];

		[Desc("Damage types that gib the unit.")]
		public readonly BitSet<DamageType> GibTypes = new("ExplosionDeath");

		[Desc("Pieces thrown (a minimum and a maximum).")]
		public readonly int MinPieces = 5;
		public readonly int MaxPieces = 8;

		[Desc("How far a piece lands from the body, in cells (a minimum and a maximum).")]
		public readonly int MinDistance = 1;
		public readonly int MaxDistance = 4;

		[Desc("Ticks a piece is in the air, and the height of its arc.")]
		public readonly int Flight = 16;
		public readonly WDist Height = new(1280);

		[Desc("The blood splash where a piece lands (an image and sequences small1 to small7, as fx-blood has).")]
		public readonly string BloodImage = "fx-blood";

		public readonly string Palette = "effect";

		public override object Create(ActorInitializer init) { return new ThrowsGibs(this); }
	}

	public class ThrowsGibs : INotifyKilled
	{
		readonly ThrowsGibsInfo info;

		public ThrowsGibs(ThrowsGibsInfo info) { this.info = info; }

		void INotifyKilled.Killed(Actor self, AttackInfo e)
		{
			if (info.Parts.Length == 0 || !e.Damage.DamageTypes.Overlaps(info.GibTypes))
				return;

			var world = self.World;
			var random = world.SharedRandom;
			var start = self.CenterPosition;
			var pieces = random.Next(info.MinPieces, info.MaxPieces + 1);
			var born = world.WorldTick;

			for (var i = 0; i < pieces; i++)
			{
				var part = info.Parts[random.Next(info.Parts.Length)];
				var angle = random.Next(1024);
				var distance = random.Next(info.MinDistance * 1024, info.MaxDistance * 1024 + 1);
				var end = start + new WVec(distance, 0, 0).Rotate(WRot.FromYaw(new WAngle(angle)));
				var flight = info.Flight + random.Next(-3, 4);
				var height = info.Height.Length * (50 + random.Next(51)) / 100;
				var landing = end;

				WPos Where()
				{
					var t = Math.Min(1f, (world.WorldTick - born) / (float)flight);
					var flat = start + (end - start) * Math.Min(world.WorldTick - born, flight) / flight;
					return new WPos(flat.X, flat.Y, flat.Z + (int)(4f * height * t * (1f - t)));
				}

				world.AddFrameEndTask(w =>
				{
					w.Add(new SpriteEffect(Where, () => WAngle.Zero, w, info.Image, part, info.Palette));
					w.Add(new SpriteEffect(landing, w, info.BloodImage, "small" + (1 + random.Next(7)), info.Palette, delay: flight));
				});
			}
		}
	}
}
