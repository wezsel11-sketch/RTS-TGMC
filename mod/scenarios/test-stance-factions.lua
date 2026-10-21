-- Scenario test: stances for SOM and for the xenos (test-stance covers the marine rifleman). Four pairs, one per row, 14 cells apart so a
-- rifle (range 9) cannot reach another row:
--   y 8:  SOM trooper on Hold Fire next to a runner        -> the runner must be unhurt
--   y 22: SOM trooper on Attack Anything next to a runner  -> the runner must be hurt
--   y 36: xeno runner on Hold Fire next to a Hold Fire rifleman      -> the rifleman must be unhurt
--   y 50: xeno runner on Attack Anything next to a Hold Fire rifleman -> the rifleman must be hurt
-- Prints "TEST stance-factions PASS" or "TEST stance-factions FAIL" after 300 ticks.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local function at(player, type, y)
		for _, a in ipairs(player.GetActorsByType(type)) do
			if a.Location.Y == y then return a end
		end
	end
	local somHold, somHoldRunner = at(marines, "som_trooper", 8), at(xenos, "runner", 8)
	local somAgg, somAggRunner = at(marines, "som_trooper", 22), at(xenos, "runner", 22)
	local xenoHold, xenoHoldTarget = at(xenos, "runner", 36), at(marines, "rifleman", 36)
	local xenoAgg, xenoAggTarget = at(xenos, "runner", 50), at(marines, "rifleman", 50)

	somHold.Stance = "HoldFire"
	somAgg.Stance = "AttackAnything"
	-- The runners facing a SOM trooper do not attack on their own, so only the trooper's stance decides.
	somHoldRunner.Stance = "HoldFire"
	somAggRunner.Stance = "HoldFire"
	xenoHold.Stance = "HoldFire"
	xenoAgg.Stance = "AttackAnything"
	xenoHoldTarget.Stance = "HoldFire"
	xenoAggTarget.Stance = "HoldFire"

	local function hurt(a, max) return a.IsDead or a.Health < max end
	local somHoldMax, somAggMax = somHoldRunner.MaxHealth, somAggRunner.MaxHealth
	local xenoHoldMax, xenoAggMax = xenoHoldTarget.MaxHealth, xenoAggTarget.MaxHealth

	Trigger.AfterDelay(300, function()
		local r1 = not hurt(somHoldRunner, somHoldMax)
		local r2 = hurt(somAggRunner, somAggMax)
		local r3 = not hurt(xenoHoldTarget, xenoHoldMax)
		local r4 = hurt(xenoAggTarget, xenoAggMax)
		print("DBG som hold fire kept off " .. tostring(r1) .. ", som attack anything hit " .. tostring(r2) ..
			", xeno hold fire kept off " .. tostring(r3) .. ", xeno attack anything hit " .. tostring(r4))
		print("TEST stance-factions " .. ((r1 and r2 and r3 and r4) and "PASS" or "FAIL"))
	end)
end
