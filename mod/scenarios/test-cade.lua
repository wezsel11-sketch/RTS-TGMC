-- Scenario test: a barricade covers whoever is on the side it faces. Two riflemen shoot at hunters across a barricade each: the first barricade faces the
-- rifleman (the hunter hides behind it), the second faces the hunter (the rifleman fires over it). The hunter behind the barricade takes clearly less damage.
-- Prints "TEST cade PASS" or "TEST cade FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local covered, open
	for _, h in ipairs(xenos.GetActorsByType("hunter")) do
		h.Stance = "HoldFire"
		if h.Location.Y < 8 then
			covered = h
		else
			open = h
		end
	end
	Trigger.AfterDelay(500, function()
		local coveredLost = 3000 - covered.Health
		local openLost = 3000 - open.Health
		print("TEST cade " .. ((openLost > 100 and coveredLost < openLost * 0.6) and "PASS" or "FAIL") .. " (barricade facing the shooter: " .. coveredLost .. " lost, facing the target: " .. openLost .. " lost)")
	end)
end
