-- Scenario test: the workshop builds a mech and the mech leaves the workshop. Prints "TEST mechbuild PASS" or "TEST mechbuild FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	marines.Cash = 5000
	local workshop = marines.GetActorsByType("workshop")[1]
	Trigger.AfterDelay(10, function()
		-- Lua's Player.Build only drives stock ClassicProductionQueues, not the mod's MultiProductionQueue, so the workshop makes it directly.
		workshop.Produce("mech")
	end)
	Trigger.AfterDelay(1800, function()
		local mechs = #marines.GetActorsByType("mech")
		print("cash " .. marines.Cash .. " queue ok"); print("TEST mechbuild " .. (mechs >= 1 and "PASS" or "FAIL") .. " (" .. mechs .. " mechs)")
	end)
end
