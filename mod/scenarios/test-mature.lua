-- Scenario test: a xeno grows through the maturity tiers with age. The timer is shortened by the map rules.
-- Prints "TEST mature PASS" or "TEST mature FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local runner = xenos.GetActorsByType("runner")[1]
	Trigger.AfterDelay(260, function()
		print("TEST mature " .. (runner.MaturityTier == 3 and "PASS" or "FAIL") .. " (tier " .. runner.MaturityTier .. " of 3)")
	end)
end
