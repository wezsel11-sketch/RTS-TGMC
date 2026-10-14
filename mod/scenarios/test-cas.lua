-- Scenario test: the CAS strike (the Condor, a support power on the ordnance depot) kills the xenos at the target spot and also hits a
-- marine standing in the blast. Prints "TEST cas PASS" or "TEST cas FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local depot = marines.GetActorsByType("ordnance-depot")[1]
	local hunters = xenos.GetActorsByType("hunter")
	local friend
	for _, r in ipairs(marines.GetActorsByType("rifleman")) do
		if r.Location.X == 14 then
			friend = r
		end
	end
	local friendMax = friend.MaxHealth
	for _, h in ipairs(hunters) do
		h.Stance = "HoldFire"
	end
	friend.Stance = "HoldFire"
	Trigger.AfterDelay(10, function()
		depot.ActivateCondorStrike(CPos.New(15, 10))
	end)
	Trigger.AfterDelay(400, function()
		local dead = 0
		for _, h in ipairs(hunters) do
			if h.IsDead then
				dead = dead + 1
			end
		end
		local friendHurt = friend.IsDead or friend.Health < friendMax
		print("TEST cas " .. ((dead == #hunters and friendHurt) and "PASS" or "FAIL") .. " (hunters dead " .. dead .. " of " .. #hunters .. ", friend hurt=" .. tostring(friendHurt) .. ")")
	end)
end
