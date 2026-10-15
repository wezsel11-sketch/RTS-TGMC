-- Scenario test: the workshop's mech drop lands a mech on the spot. Prints "TEST mechdrop PASS" or "TEST mechdrop FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local workshop = marines.GetActorsByType("workshop")[1]
	Trigger.AfterDelay(20, function()
		workshop.CallDropPod(CPos.New(12, 12), "mech")
	end)
	Trigger.AfterDelay(400, function()
		local mechs = #marines.GetActorsByType("mech")
		print("TEST mechdrop " .. (mechs >= 1 and "PASS" or "FAIL") .. " (" .. mechs .. " mechs)")
	end)
end
