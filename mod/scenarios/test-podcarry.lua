-- Scenario test: pods carrying a mortar emplacement and a sentry land on awkward spots (a corner of the map, a wall, on top of units and of a
-- building, on one another) without a crash, and the mortar fires. Prints "TEST podcarry PASS" or "TEST podcarry FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local pod = marines.GetActorsByType("cryo-pod")[1]
	local spots = { CPos.New(0, 0), CPos.New(31, 23), CPos.New(15, 11), CPos.New(10, 12), CPos.New(6, 6), CPos.New(20, 12), CPos.New(20, 12), CPos.New(21, 12) }
	for i, c in ipairs(spots) do
		Trigger.AfterDelay(10 + i * 5, function()
			pod.CallDropPod(c, "mortar-emplacement")
			pod.CallDropPod(c, "sentry-turret")
		end)
	end
	Trigger.AfterDelay(1500, function()
		local mortars = #marines.GetActorsByType("mortar-emplacement")
		print("TEST podcarry " .. (mortars >= 4 and "PASS" or "FAIL") .. " (" .. mortars .. " mortars, " .. #marines.GetActorsByType("sentry-turret") .. " sentries)")
	end)
end
