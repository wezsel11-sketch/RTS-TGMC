-- Scenario test: a weed node grows weeds on its own. Prints "TEST weeds PASS" or "TEST weeds FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	Trigger.AfterDelay(800, function()
		local count = #xenos.GetActorsByType("weeds")
		print("TEST weeds " .. (count >= 3 and "PASS" or "FAIL") .. " (" .. count .. " weeds)")
	end)
end
