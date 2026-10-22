-- Screenshot scene: the particles of a big blast (smoke, dust, rocks, sparks) from a Fatty strike. Run by the shot-blast map.
WorldLoaded = function()
	local depot = Player.GetPlayer("Marines").GetActorsByType("ordnance-depot")[1]
	for _, h in ipairs(Player.GetPlayer("Xenos").GetActorsByType("hunter")) do
		h.Stance = "HoldFire"
	end
	Trigger.AfterDelay(5, function()
		depot.ActivateCondorStrike(CPos.New(15, 12), "fatty")
	end)
end
