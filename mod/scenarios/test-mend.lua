-- Scenario test (see mod/test_scenarios.sh): a xeno Drone should mend a damaged hive structure without being ordered to.
-- Prints "TEST mend PASS" or "TEST mend FAIL".
WorldLoaded = function()
	local turret = Player.GetPlayer("Xenos").GetActorsByType("resin-turret")[1]
	turret.Health = 100

	Trigger.AfterDelay(600, function()
		print("TEST mend " .. (turret.Health > 100 and "PASS" or "FAIL") .. " (turret at " .. turret.Health .. " of " .. turret.MaxHealth .. ")")
	end)
end
