#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose queues this file extends.
#endregion

using System.Linq;
using OpenRA.Mods.Common.Traits;
using OpenRA.Scripting;
using OpenRA.Traits;

namespace OpenRA.Mods.TGMC.Traits
{
	[TraitLocation(SystemActors.Player)]
	[Desc("A unit queue that builds as many units at once as you own production buildings for it: two barracks train two marines " +
		"side by side, three silos hatch three xenos. Each unit still takes its full time, and each is paid for as it is built.")]
	public class MultiProductionQueueInfo : ClassicParallelProductionQueueInfo
	{
		[Desc("Most units one queue may build at once, however many buildings there are.")]
		public readonly int MaxSlots = 6;

		public override object Create(ActorInitializer init) { return new MultiProductionQueue(init, this); }
	}

	public class MultiProductionQueue : ClassicParallelProductionQueue
	{
		readonly Actor self;
		readonly MultiProductionQueueInfo info;
		string lastQueued;

		/// <summary>Repeat build: when the queue empties, queue the item it last built again (it waits for cash like any item).</summary>
		public bool Repeat { get; set; }

		public MultiProductionQueue(ActorInitializer init, MultiProductionQueueInfo info)
			: base(init, info)
		{
			self = init.Self;
			this.info = info;
		}

		/// <summary>How many units this queue builds at once: one per working production building.</summary>
		public int Slots
		{
			get
			{
				var count = self.World.ActorsWithTrait<Production>()
					.Count(p => !p.Trait.IsTraitDisabled && !p.Trait.IsTraitPaused && p.Actor.Owner == self.Owner
						&& p.Trait.Info.Produces.Contains(Info.Type));

				return System.Math.Clamp(count, 1, info.MaxSlots);
			}
		}

		protected override void TickInner(Actor self, bool allProductionPaused)
		{
			CancelUnbuildableItems();

			if (allProductionPaused)
				return;

			if (Queue.Count > 0)
				lastQueued = Queue[^1].Item;
			else if (Repeat && lastQueued != null && BuildableItems().Any(a => a.Name == lastQueued))
				ResolveOrder(self, Order.StartProduction(self, lastQueued, 1));

			// A finished unit keeps asking to leave until a building has room for it.
			foreach (var item in Queue.Where(i => !i.Paused && i.Done).ToList())
				item.Tick(playerResources);

			// The first few waiting items, one per building, all progress each tick.
			foreach (var item in Queue.Where(i => !i.Paused && !i.Done).Take(Slots).ToList())
				item.Tick(playerResources);
		}

		public override int RemainingTimeActual(ProductionItem item)
		{
			return item.RemainingTimeActual;
		}
	}
}

namespace OpenRA.Mods.TGMC.Scripting
{
	using OpenRA.Mods.TGMC.Traits;

	[ScriptPropertyGroup("Production")]
	public class MultiProductionProperties : ScriptPlayerProperties, Requires<MultiProductionQueueInfo>
	{
		public MultiProductionProperties(ScriptContext context, Player player)
			: base(context, player) { }

		[Desc("Turn repeat build on or off for every unit queue of this player.")]
		public void SetRepeat(bool on)
		{
			foreach (var q in Player.PlayerActor.TraitsImplementing<MultiProductionQueue>())
				q.Repeat = on;
		}

		[Desc("True if repeat build is on for the player's unit queues.")]
		public bool RepeatOn => Player.PlayerActor.TraitsImplementing<MultiProductionQueue>().Any(q => q.Repeat);

		[Desc("Queue one unit in the unit queue that builds it, as if its palette icon were clicked. Returns false if no queue can.")]
		public bool QueueUnit(string actorType)
		{
			var queue = Player.PlayerActor.TraitsImplementing<MultiProductionQueue>().FirstOrDefault(q => q.Enabled && q.BuildableItems().Any(a => a.Name == actorType));
			if (queue == null)
				return false;

			queue.ResolveOrder(queue.Actor, Order.StartProduction(queue.Actor, actorType, 1));
			return true;
		}
	}
}
