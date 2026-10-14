-- Screenshot scene: the Condor on its run toward a spot to the south-east of the depot, to check which way the jet faces.
WorldLoaded = function()
	local depot = Player.GetPlayer("Marines").GetActorsByType("ordnance-depot")[1]
	Trigger.AfterDelay(5, function()
		depot.ActivateCondorStrike(CPos.New(16, 12), "cas")
	end)
end
