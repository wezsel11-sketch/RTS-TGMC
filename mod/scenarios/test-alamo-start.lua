-- Scenario test: the marines start on the Alamo (their base on the landing zone). Prints "TEST alamo-start PASS" or "TEST alamo-start FAIL".
WorldLoaded = function()
	Trigger.AfterDelay(10, function()
		local alamo = Player.GetPlayer("Marines").GetActorsByType("alamo")
		local ok = #alamo == 1
		print("TEST alamo-start " .. (ok and "PASS" or "FAIL") .. " (" .. #alamo .. " alamo)")
	end)
end
