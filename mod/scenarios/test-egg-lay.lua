-- Scenario test: a carrier uses its Lay Egg ability (slot 2) on bare ground, away from any weeds, and an egg appears beside it.
-- Prints "TEST egg-lay PASS" or "TEST egg-lay FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local marines = Player.GetPlayer("Marines")
	marines.GetActorsByType("rifleman")[1].Stance = "HoldFire"
	local carrier = xenos.GetActorsByType("carrier")[1]
	Trigger.AfterDelay(10, function()
		carrier.UseAbility(2)
	end)
	Trigger.AfterDelay(80, function()
		local eggs = #xenos.GetActorsByType("egg")
		print("TEST egg-lay " .. (eggs >= 1 and "PASS" or "FAIL") .. " (" .. eggs .. " eggs)")
	end)
end
