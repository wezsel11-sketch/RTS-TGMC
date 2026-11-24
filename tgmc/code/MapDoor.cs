#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Collections.Generic;
using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Mods.Common.Traits.Render;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("A door: one of a converted TGMC map, or a resin door the xenos build (FriendsOnly, CloseDelay, Walls). It opens by itself, with TGMC's animation, when a unit comes near, and closes again a little after the last unit has gone. " +
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

		[Desc("Only units allied with the door's owner open it and pass. Everyone else has to break it down.")]
		public readonly bool FriendsOnly = false;

		[Desc("Ticks with nobody near before an open door closes again. 0: it stays open for good.")]
		public readonly int CloseDelay = 0;

		[Desc("With one of these actors in the cell east or west of it, the door is part of a wall that runs east to west: " +
			"it uses the sequences h<Prefix>-closed, -opening and -closing, and has SidewaysCondition.")]
		public readonly string[] Walls = [];

		[GrantedConditionReference]
		public readonly string SidewaysCondition = null;

		[Desc("Units of these factions have to pry the door open: it opens only after PryTicks with one of them beside it (TGMC's xenos " +
			"force a colony door; marines just walk through).")]
		public readonly HashSet<string> PryFactions = [];
		public readonly int PryTicks = 0;

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
		int scan;
		bool started;
		int openToken = Actor.InvalidConditionToken;
		int sidewaysToken = Actor.InvalidConditionToken;
		int quiet;
		int pry;
		string prefix;

		public MapDoor(Actor self, MapDoorInfo info)
		{
			this.info = info;
			building = self.Trait<Building>();
			body = self.TraitsImplementing<WithSpriteBody>().First();
			phase = info.StartsOpen ? Phase.Open : Phase.Closed;
			scan = self.World.SharedRandom.Next(8);
			prefix = info.Prefix;
		}

		bool Friend(Actor self, Actor other) { return !info.FriendsOnly || other.Owner.IsAlliedWith(self.Owner); }

		// Which way the door stands: across a wall that runs east to west, or (the default) across one that runs north to south.
		void Turn(Actor self)
		{
			if (info.Walls.Length == 0)
				return;

			var influence = self.World.WorldActor.Trait<BuildingInfluence>();
			var sideways = new[] { new CVec(1, 0), new CVec(-1, 0) }
				.Any(v => influence.GetBuildingsAt(self.Location + v).Any(a => !a.IsDead && info.Walls.Contains(a.Info.Name)));
			if (sideways == (prefix != info.Prefix))
				return;

			prefix = sideways ? "h" + info.Prefix : info.Prefix;
			if (info.SidewaysCondition != null)
				sidewaysToken = sideways ? self.GrantCondition(info.SidewaysCondition) : self.RevokeCondition(sidewaysToken);
			if (phase == Phase.Closed)
				body.PlayCustomAnimationRepeating(self, prefix + "-closed");
		}

		void Close(Actor self)
		{
			phase = Phase.Closing;
			self.World.ActorMap.AddInfluence(self, building);
			if (openToken != Actor.InvalidConditionToken)
				openToken = self.RevokeCondition(openToken);
			Fx.Sound(self.World, self.CenterPosition, info.CloseSound);
			body.PlayCustomAnimation(self, prefix + "-closing", () =>
			{
				phase = Phase.Closed;
				body.PlayCustomAnimationRepeating(self, prefix + "-closed");
			});
		}

		public bool IsOpen => phase == Phase.Open;
		public bool BlocksSight => info.BlocksSight && phase != Phase.Open;

		void INotifyAddedToWorld.AddedToWorld(Actor self) { }

		bool Near(Actor self)
		{
			return self.World.FindActorsInCircle(self.CenterPosition, info.Radius)
				.Any(a => a != self && !a.IsDead && a.IsInWorld && a.Info.HasTraitInfo<MobileInfo>() && Friend(self, a));
		}

		void Open(Actor self)
		{
			if (phase != Phase.Closed)
				return;

			phase = Phase.Opening;
			Fx.Sound(self.World, self.CenterPosition, info.OpenSound);
			body.PlayCustomAnimation(self, prefix + "-opening", () =>
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
					body.PlayCustomAnimationRepeating(self, prefix + "-closed");
			}

			if (++scan < 6)
				return;

			scan = 0;
			// A closed door opens when a unit comes near. An opened map door stays open; a resin door closes behind the last xeno.
			if (phase == Phase.Closed)
			{
				Turn(self);
				var near = self.World.FindActorsInCircle(self.CenterPosition, info.Radius)
					.Where(a => a != self && !a.IsDead && a.IsInWorld && a.Info.HasTraitInfo<MobileInfo>() && Friend(self, a)).ToList();
				if (near.Count == 0)
					pry = 0;
				else if (near.Any(a => !Pries(a)))
					Open(self);
				else if (!near.Any(a => (a.CenterPosition - self.CenterPosition).HorizontalLengthSquared <= 1536L * 1536))
					pry = 0; // still on the way: the prying starts beside the door
				else if ((pry += 6) >= info.PryTicks)
				{
					pry = 0;
					Open(self);
				}
			}
			else if (phase == Phase.Open && info.CloseDelay > 0)
			{
				quiet = Near(self) ? 0 : quiet + 6;
				if (quiet >= info.CloseDelay && !self.World.ActorMap.GetActorsAt(self.Location).Any(a => a != self))
				{
					quiet = 0;
					Close(self);
				}
			}
		}

		bool ITemporaryBlocker.IsBlocking(Actor self, CPos cell)
		{
			return phase != Phase.Open && cell == self.Location;
		}

		// A unit that has to pry the door cannot count on it opening for it: told otherwise, the mover walks through the shut door.
		bool ITemporaryBlocker.CanRemoveBlockage(Actor self, Actor blocking) { return Friend(self, blocking) && !Pries(blocking); }

		bool Pries(Actor a) { return info.PryTicks > 0 && info.PryFactions.Contains(a.Owner.Faction.InternalName); }

		void INotifyBlockingMove.OnNotifyBlockingMove(Actor self, Actor blocking)
		{
			// A unit that has to pry the door waits for the tick's pry count instead (ITick above).
			if (phase == Phase.Closed && Friend(self, blocking) && !Pries(blocking))
				Open(self);
		}
	}
}
