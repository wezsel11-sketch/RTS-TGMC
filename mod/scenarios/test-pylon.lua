-- Scenario test: a recovery pylon mends a wounded xeno nearby. Prints "TEST pylon PASS" or "TEST pylon FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local patient = xenos.GetActorsByType("runner")[1]
	patient.Health = 30
	Trigger.AfterDelay(400, function()
		print("TEST pylon " .. (patient.Health > 70 and "PASS" or "FAIL") .. " (patient at " .. patient.Health .. " of " .. patient.MaxHealth .. ")")
	end)
end
