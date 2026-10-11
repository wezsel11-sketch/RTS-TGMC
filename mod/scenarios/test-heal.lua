-- Scenario test (see mod/test_scenarios.sh): a corpsman should heal wounded marines without being ordered to.
-- Prints "TEST heal PASS" or "TEST heal FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local patients = marines.GetActorsByType("rifleman")
	for _, a in ipairs(patients) do
		a.Health = 40
	end

	Trigger.AfterDelay(600, function()
		local healed = true
		for _, a in ipairs(patients) do
			if a.Health <= 40 then
				healed = false
			end
		end
		print("TEST heal " .. (healed and "PASS" or "FAIL") .. " (first patient at " .. patients[1].Health .. " of " .. patients[1].MaxHealth .. ")")
	end)
end
