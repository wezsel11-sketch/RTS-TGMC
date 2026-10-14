-- Scenario test: the mortar emplacement hits a target the mortarman could not reach, the howitzer one still further out.
-- Prints "TEST emplacement PASS" or "TEST emplacement FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local silos = xenos.GetActorsByType("crusher")
	local near, far = silos[1], silos[2]
	local n0, f0 = near.Health, far.Health
	Trigger.AfterDelay(500, function()
		local nearHit, farHit = near.Health < n0, far.Health < f0
		print("TEST emplacement " .. ((nearHit and farHit) and "PASS" or "FAIL") .. " (mortar target " .. n0 .. " -> " .. near.Health .. ", howitzer target " .. f0 .. " -> " .. far.Health .. ")")
	end)
end
