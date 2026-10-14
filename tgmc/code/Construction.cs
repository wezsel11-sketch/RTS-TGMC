#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("A building that fades in when it is placed, instead of popping up whole. Buildings that exist at the start of the match do not fade.")]
	public class FadesInOnBuildInfo : TraitInfo
	{
		[Desc("Ticks the fade takes.")]
		public readonly int Duration = 60;

		[Desc("How solid the building is on the first tick, from 0 to 100.")]
		public readonly int StartPercent = 15;

		public override object Create(ActorInitializer init) { return new FadesInOnBuild(init.Self, this); }
	}

	public class FadesInOnBuild : IRenderModifier
	{
		readonly FadesInOnBuildInfo info;
		readonly int born;

		public FadesInOnBuild(Actor self, FadesInOnBuildInfo info)
		{
			this.info = info;

			// -1: placed before the match began (or loaded by a map), so already standing.
			born = self.World.WorldTick == 0 ? -1 : self.World.WorldTick;
		}

		IEnumerable<IRenderable> IRenderModifier.ModifyRender(Actor self, WorldRenderer wr, IEnumerable<IRenderable> r)
		{
			if (born < 0)
				return r;

			var age = self.World.WorldTick - born;
			if (age >= info.Duration)
				return r;

			var alpha = (info.StartPercent + (100 - info.StartPercent) * age / info.Duration) / 100f;
			return r.Select(x => x is IModifyableRenderable m ? m.WithAlpha(alpha) : x);
		}

		IEnumerable<Rectangle> IRenderModifier.ModifyScreenBounds(Actor self, WorldRenderer wr, IEnumerable<Rectangle> bounds)
		{
			return bounds;
		}
	}
	[Desc("A barricade that faces away from the base: it looks for the nearest friendly building and grants the condition for the " +
		"side it lies on (the cade-north, cade-south, cade-east or cade-west conditions), so the rules can show the right sprite.")]
	public class FacesOutwardInfo : TraitInfo
	{
		[GrantedConditionReference]
		public readonly string NorthCondition = "side-north";

		[GrantedConditionReference]
		public readonly string SouthCondition = "side-south";

		[GrantedConditionReference]
		public readonly string EastCondition = "side-east";

		[GrantedConditionReference]
		public readonly string WestCondition = "side-west";

		public override object Create(ActorInitializer init) { return new FacesOutward(this); }
	}

	public class FacesOutward : INotifyCreated
	{
		readonly FacesOutwardInfo info;

		public FacesOutward(FacesOutwardInfo info)
		{
			this.info = info;
		}

		void INotifyCreated.Created(Actor self)
		{
			var here = self.World.Map.CenterOfCell(self.Location);
			var anchor = self.World.ActorsHavingTrait<Building>()
				.Where(a => a != self && a.Owner == self.Owner && !a.Disposed && !a.Info.HasTraitInfo<LineBuildNodeInfo>())
				.OrderBy(a => (a.CenterPosition - here).HorizontalLengthSquared)
				.FirstOrDefault();

			// Without a building to turn away from, face south, the way the art is drawn.
			var away = anchor == null ? new WVec(0, 1024, 0) : here - anchor.CenterPosition;
			string condition;
			if (System.Math.Abs(away.X) > System.Math.Abs(away.Y))
				condition = away.X > 0 ? info.EastCondition : info.WestCondition;
			else
				condition = away.Y > 0 ? info.SouthCondition : info.NorthCondition;

			self.GrantCondition(condition);
		}
	}
}
