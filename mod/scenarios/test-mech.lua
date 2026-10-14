-- Scenario test: the mech stands against two hunters and wins, using both its guns. Prints "TEST mech PASS" or "TEST mech FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local mech = marines.GetActorsByType("mech")[1]
	local hunters = xenos.GetActorsByType("hunter")
	local mechMax = mech.MaxHealth
	Trigger.AfterDelay(500, function()
		local dead = 0
		for _, h in ipairs(hunters) do
			if h.IsDead then
				dead = dead + 1
			end
		end
		local lost = mech.IsDead and mechMax or mechMax - mech.Health
		print("TEST mech " .. ((not mech.IsDead and dead == 2) and "PASS" or "FAIL") .. " (hunters dead " .. dead .. ", mech lost " .. lost .. " of " .. mechMax .. ")")
	end)
end
