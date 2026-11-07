#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[Desc("The town bell: every unit of the owner within Radius of the chosen spot drops what it is doing and runs to the nearest " +
		"base building (BaseTypes). The answer to a raid on an outlying miner or weed node.")]
	public class RecallPowerInfo : SupportPowerInfo
	{
		[Desc("Cells around the target whose units are called home.")]
		public readonly int Radius = 10;

		[ActorReference]
		[Desc("Buildings the units run to: the nearest one to each unit.")]
		public readonly string[] BaseTypes = [];

		public readonly string[] Sounds = [];

		public override object Create(ActorInitializer init) { return new RecallPower(init.Self, this); }
	}

	public class RecallPower : SupportPower
	{
		readonly RecallPowerInfo info;

		public RecallPower(Actor self, RecallPowerInfo info)
			: base(self, info)
		{
			this.info = info;
		}

		public override void Activate(Actor self, Order order, SupportPowerManager manager)
		{
			base.Activate(self, order, manager);
			Recall(self, self.World.Map.CellContaining(order.Target.CenterPosition));
		}

		public void Recall(Actor self, CPos centre)
		{
			var world = self.World;
			var homes = world.Actors.Where(a => a.Owner == self.Owner && a.IsInWorld && !a.IsDead && info.BaseTypes.Contains(a.Info.Name)).ToList();
			if (homes.Count == 0)
				return;

			Fx.Sound(world, world.Map.CenterOfCell(centre), info.Sounds);
			foreach (var unit in world.FindActorsInCircle(world.Map.CenterOfCell(centre), WDist.FromCells(info.Radius)))
			{
				if (unit.Owner != self.Owner || unit.IsDead || !unit.IsInWorld || unit.TraitOrDefault<Mobile>() == null)
					continue;

				var home = homes.MinBy(h => (h.Location - unit.Location).LengthSquared);
				unit.QueueActivity(false, unit.Trait<IMove>().MoveTo(home.Location, 2));
			}
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using OpenRA.Mods.TGMC.Traits;
	using OpenRA.Scripting;

	[ScriptPropertyGroup("Support Powers")]
	public class RecallProperties : ScriptActorProperties, Requires<RecallPowerInfo>
	{
		public RecallProperties(ScriptContext context, Actor self)
			: base(context, self) { }

		[Desc("Ring this actor's town bell at the cell at once, charged or not.")]
		public void CallRecall(CPos target)
		{
			Self.Trait<RecallPower>().Recall(Self, target);
		}
	}
}
