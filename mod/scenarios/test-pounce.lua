-- Scenario test: a runner leaps at a marine from range and lands a hit. Prints "TEST pounce PASS" or "TEST pounce FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local marine = marines.GetActorsByType("rifleman")[1]
	marine.Stance = "HoldFire"
	local runner = xenos.GetActorsByType("runner")[1]
	local marineMax = marine.MaxHealth
	Trigger.AfterDelay(5, function()
		runner.Attack(marine)
	end)
	Trigger.AfterDelay(60, function()
		local lost = marine.IsDead and marineMax or marineMax - marine.Health
		print("TEST pounce " .. (lost >= 30 and "PASS" or "FAIL") .. " (marine lost " .. lost .. " within 2.4 seconds)")
	end)
end
