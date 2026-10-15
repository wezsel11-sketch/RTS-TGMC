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
		"Closed, it blocks movement and bullets; units path through it as through a gate. Needs the sequences <Prefix>-closed, -opening, -open and -closing.")]
	public class MapDoorInfo : TraitInfo, ITemporaryBlockerInfo, Requires<BuildingInfo>, Requires<WithSpriteBodyInfo>
	{
		public readonly string Prefix = "";

		[Desc("The door starts open (a blast door that TGMC maps leave open).")]
		public readonly bool StartsOpen = false;

		[Desc("A unit this close opens the door.")]
		public readonly WDist Radius = new(1900);

		[Desc("Ticks the door stays open after the last unit left.")]
		public readonly int CloseDelay = 60;

		public readonly string[] OpenSound = ["door-open.ogg"];
		public readonly string[] CloseSound = ["door-close.ogg"];

		public override object Create(ActorInitializer init) { return new MapDoor(init.Self, this); }
	}

	public class MapDoor : ITick, ITemporaryBlocker, INotifyBlockingMove, INotifyAddedToWorld
	{
		enum Phase { Closed, Opening, Open, Closing }

		readonly MapDoorInfo info;
		readonly Building building;
		readonly WithSpriteBody body;
		Phase phase;
		int wait;
		int scan;
		bool started;

		public MapDoor(Actor self, MapDoorInfo info)
		{
			this.info = info;
			building = self.Trait<Building>();
			body = self.Trait<WithSpriteBody>();
			phase = info.StartsOpen ? Phase.Open : Phase.Closed;
			scan = self.World.SharedRandom.Next(8);
		}

		public bool IsOpen => phase == Phase.Open;

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
				wait = info.CloseDelay;
				return;
			}

			phase = Phase.Opening;
			Fx.Sound(self.World, self.CenterPosition, info.OpenSound);
			body.PlayCustomAnimation(self, info.Prefix + "-opening", () =>
			{
				phase = Phase.Open;
				wait = info.CloseDelay;
				self.World.ActorMap.RemoveInfluence(self, building);
				body.PlayCustomAnimationRepeating(self, info.Prefix + "-open");
			});
		}

		void Close(Actor self)
		{
			phase = Phase.Closing;
			Fx.Sound(self.World, self.CenterPosition, info.CloseSound);
			self.World.ActorMap.AddInfluence(self, building);
			body.PlayCustomAnimation(self, info.Prefix + "-closing", () =>
			{
				phase = Phase.Closed;
				body.PlayCustomAnimationRepeating(self, info.Prefix + "-closed");
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
					body.PlayCustomAnimationRepeating(self, info.Prefix + "-open");
				}
				else
					body.PlayCustomAnimationRepeating(self, info.Prefix + "-closed");
			}

			if (++scan < 6)
				return;

			scan = 0;
			if (phase == Phase.Closed || phase == Phase.Closing)
			{
				if (phase == Phase.Closed && Near(self))
					Open(self);
			}
			else if (phase == Phase.Open)
			{
				if (Near(self))
					wait = info.CloseDelay;
				else if ((wait -= 6) <= 0)
					Close(self);
			}
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
