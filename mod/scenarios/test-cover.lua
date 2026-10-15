-- Scenario test: a wall stops rifle bullets. Two rifleman and hunter pairs stand five cells apart; a wall stands between the pair in the south
-- and not between the pair in the north. Only the hunter in the open is hurt. Prints "TEST cover PASS" or "TEST cover FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local covered, open
	for _, h in ipairs(xenos.GetActorsByType("hunter")) do
		h.Stance = "HoldFire"
		if h.Location.Y > 8 then
			covered = h
		else
			open = h
		end
	end
	Trigger.AfterDelay(400, function()
		local coveredLost = 3000 - covered.Health
		local openLost = open.IsDead and 3000 or 3000 - open.Health
		print("TEST cover " .. ((openLost > 100 and coveredLost == 0) and "PASS" or "FAIL") .. " (open lost " .. openLost .. ", behind the wall lost " .. coveredLost .. ")")
	end)
end
