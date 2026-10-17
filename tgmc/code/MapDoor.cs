#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Traits.Render;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("A door of a converted TGMC map. It opens by itself, with TGMC's animation, when a unit comes near, and closes again a little after the last unit has gone. " +
		"Closed, it blocks movement and bullets; units path through it as through a gate. Needs the sequences <Prefix>-closed, -opening and -open. Once open, it stays open.")]
	public class MapDoorInfo : TraitInfo, ITemporaryBlockerInfo, Requires<BuildingInfo>, Requires<WithSpriteBodyInfo>
	{
		public readonly string Prefix = "";

		[Desc("The door starts open (a blast door that TGMC maps leave open).")]
		public readonly bool StartsOpen = false;

		[Desc("A closed door stops the view as well as movement. Glass doors (security, medical, research) do not.")]
		public readonly bool BlocksSight = true;

		[Desc("A unit this close opens the door.")]
		public readonly WDist Radius = new(1900);

		
		[GrantedConditionReference]
		[Desc("Condition granted once the door is open: the open body (a second WithSpriteBody that needs it) takes over from the closed one.")]
		public readonly string OpenCondition = "door-open";

		public readonly string[] OpenSound = ["door-open.ogg"];
		public readonly string[] CloseSound = ["door-close.ogg"];

		public override object Create(ActorInitializer init) { return new MapDoor(init.Self, this); }
	}

	public class MapDoor : ITick, ITemporaryBlocker, INotifyBlockingMove, INotifyAddedToWorld
	{
		enum Phase { Closed, Opening, Open }

		readonly MapDoorInfo info;
		readonly Building building;
		readonly WithSpriteBody body;
		Phase phase;
		int scan;
		bool started;
		int openToken = Actor.InvalidConditionToken;

		public MapDoor(Actor self, MapDoorInfo info)
		{
			this.info = info;
			building = self.Trait<Building>();
			body = self.TraitsImplementing<WithSpriteBody>().First();
			phase = info.StartsOpen ? Phase.Open : Phase.Closed;
			scan = self.World.SharedRandom.Next(8);
		}

		public bool IsOpen => phase == Phase.Open;
		public bool BlocksSight => info.BlocksSight && phase != Phase.Open;

		void INotifyAddedToWorld.AddedToWorld(Actor self) { }

		bool Near(Actor self)
		{
			return self.World.FindActorsInCircle(self.CenterPosition, info.Radius)
				.Any(a => a != self && !a.IsDead && a.IsInWorld && a.Info.HasTraitInfo<MobileInfo>());
		}

		void Open(Actor self)
		{
			if (phase == Phase.Opening || phase == Phase.Open)
			{
				return;
			}

			phase = Phase.Opening;
			Fx.Sound(self.World, self.CenterPosition, info.OpenSound);
			body.PlayCustomAnimation(self, info.Prefix + "-opening", () =>
			{
				phase = Phase.Open;
				self.World.ActorMap.RemoveInfluence(self, building);
				// From now on the open body shows the open model, whatever the closed body does (damage states and the like reset it).
				if (openToken == Actor.InvalidConditionToken)
					openToken = self.GrantCondition(info.OpenCondition);
			});
		}

		void ITick.Tick(Actor self)
		{
			if (!started)
			{
				started = true;
				if (phase == Phase.Open)
				{
					self.World.ActorMap.RemoveInfluence(self, building);
					if (openToken == Actor.InvalidConditionToken)
						openToken = self.GrantCondition(info.OpenCondition);
				}
				else
					body.PlayCustomAnimationRepeating(self, info.Prefix + "-closed");
			}

			if (++scan < 6)
				return;

			scan = 0;
			// A closed door opens when a unit comes near. An opened door stays open: it never closes again.
			if (phase == Phase.Closed && Near(self))
				Open(self);
		}

		bool ITemporaryBlocker.IsBlocking(Actor self, CPos cell)
		{
			return phase != Phase.Open && cell == self.Location;
		}

		bool ITemporaryBlocker.CanRemoveBlockage(Actor self, Actor blocking) { return true; }

		void INotifyBlockingMove.OnNotifyBlockingMove(Actor self, Actor blocking)
		{
			if (phase == Phase.Closed)
				Open(self);
		}
	}
}
