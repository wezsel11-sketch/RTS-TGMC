-- Screenshot scene: a napalm strike (and the burning ground it leaves) on a group of xenos. Run by the shot-napalm map.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local depot = marines.GetActorsByType("ordnance-depot")[1]
	for _, h in ipairs(Player.GetPlayer("Xenos").GetActorsByType("hunter")) do
		h.Stance = "HoldFire"
	end
	Trigger.AfterDelay(5, function()
		depot.ActivateCondorStrike(CPos.New(15, 12), "napalm")
	end)
end
