#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.Linq;
using OpenRA.Mods.Common;
using OpenRA.Mods.Common.Traits;
using OpenRA.Primitives;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.World)]
	[Desc("The start of each side depends on the faction the player picked, not on the map slot: at the start of the game every playable player " +
		"gets the starting actors of its faction around its start location, and loses what the map placed for it. Each entry is " +
		"'actor|dx|dy|facing' (cells from the start location, facing in OpenRA angle units). " +
		"With the lobby's landing intro, the marines' and SOM's units ride down in Transport and walk out of it; their buildings stand from the start.")]
	public class FactionStartInfo : TraitInfo
	{
		public readonly string[] Marines = [];
		public readonly string[] Som = [];
		public readonly string[] Xenos = [];

		[ActorReference]
		[Desc("The dropship of the landing intro. It needs Dropship with LandAtStart, and the door and launch conditions of the alamo.")]
		public readonly string Transport = "alamo-drop";

		[Desc("Where the ship sets down, in cells from the start location: north of the base, its ramp toward it.")]
		public readonly CVec TransportOffset = new(0, -13);

		[Desc("Where the units step out, in cells from the ship.")]
		public readonly CVec HatchOffset = new(0, 9);

		[Desc("Ticks the doors take to open or close, and ticks between two units stepping out.")]
		public readonly int DoorTicks = 18;
		public readonly int UnloadInterval = 8;

		public override object Create(ActorInitializer init) { return new FactionStart(this); }
	}

	public class FactionStart : IWorldLoaded, ITick
	{
		// One landing: the ship, who is still aboard, and the ticks since touchdown (-1 while it is coming down).
		sealed class Landing
		{
			public Player Owner;
			public Actor Ship;
			public CPos Hatch;
			public readonly System.Collections.Generic.Queue<(string Actor, CPos Cell, WAngle Facing)> Aboard = new();
			public int Down = -1;
			public int Empty = -1;
		}

		readonly FactionStartInfo info;
		readonly System.Collections.Generic.List<Landing> landings = [];

		public FactionStart(FactionStartInfo info) { this.info = info; }

		static Actor Place(World w, Player p, string actor, CPos cell, WAngle facing)
		{
			return w.CreateActor(actor, new TypeDictionary { new LocationInit(cell), new OwnerInit(p), new FacingInit(facing) });
		}

		void IWorldLoaded.WorldLoaded(World w, OpenRA.Graphics.WorldRenderer wr)
		{
			var intro = w.Type == WorldType.Regular && Options.Enabled(w, Options.LandingIntro, true) && w.Map.Rules.Actors.ContainsKey(info.Transport);
			foreach (var p in w.Players.Where(pl => pl.Playable && !pl.NonCombatant && pl.HomeLocation != CPos.Zero))
			{
				var faction = p.Faction.InternalName;
				var entries = faction switch
				{
					"marines" => info.Marines,
					"som" => info.Som,
					"xenos" => info.Xenos,
					_ => []
				};

				if (entries.Length == 0)
					continue;

				// What the map placed for this player goes; the faction's own start replaces it.
				foreach (var a in w.Actors.Where(a => a.Owner == p && a != p.PlayerActor && !a.IsDead).ToList())
					a.Dispose();

				Landing landing = null;
				foreach (var entry in entries)
				{
					var parts = entry.Trim().Split('|');
					var cell = p.HomeLocation + new CVec(int.Parse(parts[1]), int.Parse(parts[2]));
					var facing = new WAngle(int.Parse(parts[3]));

					// Whatever can walk rides down in the ship; buildings stand from the start, so the player is never without a base.
					if (intro && faction != "xenos" && w.Map.Rules.Actors[parts[0]].HasTraitInfo<MobileInfo>())
					{
						landing ??= new Landing { Owner = p };
						landing.Aboard.Enqueue((parts[0], cell, facing));
					}
					else
						Place(w, p, parts[0], cell, facing);
				}

				if (landing == null)
					continue;

				var at = w.Map.Clamp(p.HomeLocation + info.TransportOffset);
				landing.Ship = Place(w, p, info.Transport, at, WAngle.Zero);
				landing.Hatch = at + info.HatchOffset;
				landings.Add(landing);
			}
		}

		static void Grant(Actor ship, string condition, int duration = 0)
		{
			ship.TraitsImplementing<ExternalCondition>().FirstOrDefault(t => t.Info.Condition == condition)?.GrantCondition(ship, ship, duration);
		}

		void ITick.Tick(Actor self)
		{
			for (var i = landings.Count - 1; i >= 0; i--)
			{
				var l = landings[i];
				var w = self.World;
				var gone = l.Ship.IsDead || !l.Ship.IsInWorld;

				// Touchdown: the doors open.
				if (!gone && l.Down < 0)
				{
					if (!l.Ship.Trait<Dropship>().Landed)
						continue;

					l.Down = 0;
					Grant(l.Ship, "doors-opening", info.DoorTicks);
					w.WorldActor.TraitOrDefault<ScreenShaker>()?.AddEffect(12, l.Ship.CenterPosition, 2);
					TgmcEventLog.Post(w, l.Owner, "event-alamo-down", l.Ship.CenterPosition);
				}

				l.Down++;
				if (!gone && l.Down == info.DoorTicks)
					Grant(l.Ship, "doors-open");

				// One unit steps out every few ticks and walks to its place. A ship that is gone puts the rest down where they belong.
				while (l.Aboard.Count > 0 && (gone || (l.Down > info.DoorTicks && l.Down % info.UnloadInterval == 0)))
				{
					var (actor, cell, facing) = l.Aboard.Dequeue();
					var mobile = w.Map.Rules.Actors[actor].TraitInfo<MobileInfo>();
					var from = !gone && mobile.CanEnterCell(w, null, l.Hatch) ? l.Hatch : cell;
					var unit = Place(w, l.Owner, actor, from, facing);
					if (from != cell)
						unit.QueueActivity(unit.Trait<IMove>().MoveTo(cell, 0));

					if (!gone)
						break;
				}

				if (l.Aboard.Count > 0)
					continue;

				// Empty: the doors close and the ship climbs away (its Dropship trait wakes on the launch condition and removes it).
				if (l.Empty < 0)
				{
					l.Empty = l.Down;
					if (!gone)
						Grant(l.Ship, "doors-closing");
				}

				if (gone || l.Down == l.Empty + info.DoorTicks)
				{
					if (!gone)
						Grant(l.Ship, "launch");

					landings.RemoveAt(i);
				}
			}
		}
	}
}
