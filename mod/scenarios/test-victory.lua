-- Scenario test (see mod/test_scenarios.sh): destroying every xeno unit and structure should win the game for the marines.
-- Prints "TEST victory PASS" or "TEST victory FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")

	Trigger.OnPlayerWon(marines, function()
		if not reported then
			reported = true
			print("TEST victory PASS (marines won)")
		end
	end)
	Trigger.OnPlayerLost(xenos, function()
		print("TEST victory note: xenos lost")
	end)

	Trigger.AfterDelay(50, function()
		Utils.Do(xenos.GetActorsByTypes({ "runner", "resin-silo", "mini-silo", "resin-turret" }), function(a)
			a.Kill()
		end)
	end)

	Trigger.AfterDelay(900, function()
		if not reported then
			reported = true
			print("TEST victory FAIL (no win after 900 ticks)")
		end
	end)
end
