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
		"'actor|dx|dy|facing' (cells from the start location, facing in OpenRA angle units).")]
	public class FactionStartInfo : TraitInfo
	{
		public readonly string[] Marines = [];
		public readonly string[] Som = [];
		public readonly string[] Xenos = [];

		public override object Create(ActorInitializer init) { return new FactionStart(this); }
	}

	public class FactionStart : IWorldLoaded
	{
		readonly FactionStartInfo info;

		public FactionStart(FactionStartInfo info) { this.info = info; }

		void IWorldLoaded.WorldLoaded(World w, OpenRA.Graphics.WorldRenderer wr)
		{
			foreach (var p in w.Players.Where(pl => pl.Playable && !pl.NonCombatant && pl.HomeLocation != CPos.Zero))
			{
				var entries = p.Faction.InternalName switch
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

				foreach (var entry in entries)
				{
					var parts = entry.Trim().Split('|');
					var cell = p.HomeLocation + new CVec(int.Parse(parts[1]), int.Parse(parts[2]));
					var facing = new WAngle(int.Parse(parts[3]));
					w.CreateActor(parts[0], new TypeDictionary
					{
						new LocationInit(cell),
						new OwnerInit(p),
						new FacingInit(facing)
					});
				}
			}
		}
	}
}
