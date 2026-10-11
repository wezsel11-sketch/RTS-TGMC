-- Scenario test (see mod/test_scenarios.sh): an engineer should repair a damaged structure without being ordered to.
-- Prints "TEST repair PASS" or "TEST repair FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local sentry = marines.GetActorsByType("sentry-turret")[1]
	sentry.Health = 100

	Trigger.AfterDelay(600, function()
		print("TEST repair " .. (sentry.Health > 100 and "PASS" or "FAIL") .. " (sentry at " .. sentry.Health .. " of " .. sentry.MaxHealth .. ")")
	end)
end
