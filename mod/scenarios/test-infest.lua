-- Scenario test (see mod/test_scenarios.sh): a facehugger latches onto a marine, who is not healed, so after the burst
-- delay the marine is dead and a xeno larva stands for the xenos. Prints "TEST infest PASS" or "TEST infest FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local host = marines.GetActorsByType("rifleman")[1]
	host.Stance = "HoldFire"

	-- the facehugger is spent by the attack
	Trigger.AfterDelay(150, function()
		local hugger = xenos.GetActorsByType("facehugger")[1]
		print("TEST infest note: facehugger " .. (hugger == nil and "spent" or "still alive") .. ", host dead=" .. tostring(host.IsDead))
	end)

	Trigger.AfterDelay(500, function()
		local larvae = #xenos.GetActorsByType("larva")
		local ok = host.IsDead and larvae >= 1
		print("TEST infest " .. (ok and "PASS" or "FAIL") .. " (host dead=" .. tostring(host.IsDead) .. ", larvae=" .. larvae .. ")")
	end)
end
