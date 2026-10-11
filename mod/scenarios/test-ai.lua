-- Scenario test (see mod/test_scenarios.sh): the Skirmish AI, set on the xeno player by the map, should spend its cash on
-- units from its silo. Prints "TEST ai PASS" or "TEST ai FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local army = { "runner", "hunter", "sentinel" }

	Trigger.AfterDelay(1000, function()
		local count = #xenos.GetActorsByTypes(army)
		print("TEST ai " .. (count >= 3 and "PASS" or "FAIL") .. " (" .. count .. " xeno units after 1000 ticks, cash " .. xenos.Cash .. ")")
	end)
end
