#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Scripting;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("A dropship that flies in when it is created: it is drawn coming down from Height over LandTicks, its shadow on the pad below, " +
		"and grants LandedCondition once down. When this trait is enabled (RequiresCondition, e.g. launch) it climbs away over " +
		"LaunchTicks and is removed. Drawing only: the actor stands on its cell throughout.")]
	public class DropshipInfo : ConditionalTraitInfo
	{
		public readonly WDist Height = new(12 * 1024);
		public readonly int LandTicks = 75;
		public readonly int LaunchTicks = 75;

		[Desc("How dark the shadow is, from 0 to 1.")]
		public readonly float ShadowAlpha = 0.45f;

		[GrantedConditionReference]
		public readonly string LandedCondition = "landed";

		public override object Create(ActorInitializer init) { return new Dropship(init.Self, this); }
	}

	public class Dropship : ConditionalTrait<DropshipInfo>, ITick, IRenderModifier
	{
		int landing;
		int launching = -1;
		int landedToken = Actor.InvalidConditionToken;

		public Dropship(Actor self, DropshipInfo info)
			: base(info)
		{
			// Placed by the map at the start: already down.
			landing = self.World.WorldTick == 0 ? info.LandTicks : 0;
		}

		public bool Landed => landing >= Info.LandTicks && launching < 0;

		protected override void TraitEnabled(Actor self)
		{
			if (launching < 0)
				launching = 0;
		}

		void ITick.Tick(Actor self)
		{
			if (launching >= 0)
			{
				if (landedToken != Actor.InvalidConditionToken)
					landedToken = self.RevokeCondition(landedToken);

				if (++launching == Info.LaunchTicks)
					self.World.AddFrameEndTask(w => self.Dispose());

				return;
			}

			if (landing < Info.LandTicks)
				landing++;
			else if (landedToken == Actor.InvalidConditionToken)
				landedToken = self.GrantCondition(Info.LandedCondition);
		}

		// Comes in fast and settles slowly; leaves slowly and speeds up.
		int Altitude()
		{
			if (launching >= 0)
			{
				var t = System.Math.Min(launching, Info.LaunchTicks);
				return Info.Height.Length * t * t / (Info.LaunchTicks * Info.LaunchTicks);
			}

			var left = Info.LandTicks - landing;
			return Info.Height.Length * left * left / (Info.LandTicks * Info.LandTicks);
		}

		IEnumerable<IRenderable> IRenderModifier.ModifyRender(Actor self, WorldRenderer wr, IEnumerable<IRenderable> r)
		{
			var altitude = Altitude();
			if (altitude == 0)
				return r;

			var list = r.ToList();
			var lift = new WVec(0, 0, altitude);

			// A black copy on the pad, fainter the higher the ship is.
			var shadowAlpha = Info.ShadowAlpha * (1f - (float)altitude / Info.Height.Length);
			var shadow = list.OfType<IModifyableRenderable>()
				.Select(m => m.WithTint(Vector3.Zero, TintModifiers.ReplaceColor | TintModifiers.IgnoreWorldTint).WithAlpha(shadowAlpha).OffsetBy(new WVec(0, 0, -1)));
			return shadow.Concat(list.Select(x => x.OffsetBy(lift)));
		}

		IEnumerable<Rectangle> IRenderModifier.ModifyScreenBounds(Actor self, WorldRenderer wr, IEnumerable<Rectangle> bounds)
		{
			return bounds;
		}
	}

	[ScriptPropertyGroup("General")]
	public class DropshipProperties : ScriptActorProperties, Requires<DropshipInfo>
	{
		readonly Dropship dropship;

		public DropshipProperties(ScriptContext context, Actor self)
			: base(context, self)
		{
			dropship = self.Trait<Dropship>();
		}

		[Desc("True once the dropship has come down, until it starts to climb away.")]
		public bool Landed => dropship.Landed;
	}
}
