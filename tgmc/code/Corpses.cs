#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Frozen;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using System.Numerics;
using OpenRA.Effects;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Traits.Render;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("Like WithDeathAnimation, but the body stays where it fell for a while and then fades away, instead of vanishing the moment " +
		"the animation ends.")]
	public class WithLingeringCorpseInfo : ConditionalTraitInfo, Requires<RenderSpritesInfo>
	{
		[SequenceReference(prefix: true)]
		[Desc("Sequence prefix to play when this actor is killed by a warhead.")]
		public readonly string DeathSequence = "die";

		[PaletteReference(nameof(DeathPaletteIsPlayerPalette))]
		[Desc("The palette used for the body.")]
		public readonly string DeathSequencePalette = "player";

		[Desc("The palette is a player palette BaseName.")]
		public readonly bool DeathPaletteIsPlayerPalette = true;

		[Desc("Death animations to use for each damage type (defined on the warheads): sequence name = DeathSequence + the suffix.")]
		public readonly FrozenDictionary<string, ImmutableArray<string>> DeathTypes = FrozenDictionary<string, ImmutableArray<string>>.Empty;

		[SequenceReference]
		[Desc("Sequence to use when the actor is killed by some non-standard means (for example a suicide).")]
		public readonly string FallbackSequence = null;

		[Desc("Ticks the body lies there at full strength after its animation ends. 500 is twenty seconds.")]
		public readonly int Linger = 500;

		[Desc("Ticks the body then takes to fade out.")]
		public readonly int Fade = 60;

		[Desc("Killed by one of these damage types, the body is charred: the fallback sequence, darkened by BurntTint.")]
		public readonly BitSet<DamageType> BurntTypes = new("FlameDeath");

		public readonly float BurntTint = 0.28f;

		public override object Create(ActorInitializer init) { return new WithLingeringCorpse(init.Self, this); }
	}

	public class WithLingeringCorpse : ConditionalTrait<WithLingeringCorpseInfo>, INotifyKilled
	{
		readonly RenderSprites rs;

		public WithLingeringCorpse(Actor self, WithLingeringCorpseInfo info)
			: base(info)
		{
			rs = self.Trait<RenderSprites>();
		}

		void INotifyKilled.Killed(Actor self, AttackInfo e)
		{
			if (IsTraitDisabled)
				return;

			string sequence;
			var burnt = false;
			if (e.Damage.DamageTypes.IsEmpty)
			{
				if (Info.FallbackSequence == null)
					return;

				sequence = Info.FallbackSequence;
			}
			else
			{
				var damageType = Info.DeathTypes.Keys.FirstOrDefault(e.Damage.DamageTypes.Contains);
				if (damageType != null)
					sequence = Info.DeathSequence + Info.DeathTypes[damageType].Random(self.World.SharedRandom);
				else if (e.Damage.DamageTypes.Overlaps(Info.BurntTypes) && Info.FallbackSequence != null)
				{
					sequence = Info.FallbackSequence;
					burnt = true;
				}
				else
					return;
			}

			var palette = Info.DeathSequencePalette;
			if (Info.DeathPaletteIsPlayerPalette)
				palette += self.Owner.InternalName;

			var pos = self.CenterPosition;
			var image = rs.GetImage(self);
			self.World.AddFrameEndTask(w => w.Add(new LyingBody(pos, w, image, sequence, palette, Info, burnt)));
		}
	}

	// The body: plays its fall once, holds the last frame, then thins out and goes.
	sealed class LyingBody : IEffect
	{
		readonly WPos pos;
		readonly Animation anim;
		readonly string palette;
		readonly WithLingeringCorpseInfo info;
		readonly bool burnt;
		int age;
		int endedAt = -1;

		public LyingBody(WPos pos, World world, string image, string sequence, string palette, WithLingeringCorpseInfo info, bool burnt)
		{
			this.pos = pos;
			this.palette = palette;
			this.info = info;
			this.burnt = burnt;
			anim = new Animation(world, image);
			anim.PlayThen(sequence, () => endedAt = age);
		}

		public void Tick(World world)
		{
			age++;
			anim.Tick();
			if (endedAt >= 0 && age - endedAt > info.Linger + info.Fade)
				world.AddFrameEndTask(w => w.Remove(this));
		}

		public IEnumerable<IRenderable> Render(WorldRenderer wr)
		{
			var alpha = 1f;
			if (endedAt >= 0)
			{
				var faded = age - endedAt - info.Linger;
				if (faded > 0)
					alpha = System.Math.Max(0f, 1f - faded / (float)System.Math.Max(1, info.Fade));
			}

			foreach (var r in anim.Render(pos, wr.Palette(palette)))
			{
				if (r is not IModifyableRenderable m)
				{
					yield return r;
					continue;
				}

				if (burnt)
					m = m.WithTint(new Vector3(info.BurntTint, info.BurntTint * 0.9f, info.BurntTint * 0.8f), m.TintModifiers);

				yield return alpha < 1f ? m.WithAlpha(alpha) : m;
			}
		}
	}
}
