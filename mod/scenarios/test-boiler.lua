-- Scenario test: the boiler lobs acid from far beyond a spitter's reach, hurts the marine it targets and leaves an acid pool.
-- Prints "TEST boiler PASS" or "TEST boiler FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local target = marines.GetActorsByType("rifleman")[1]
	local h0 = target.Health
	local pools = 0
	xenos.GetActorsByType("boiler")[1].Attack(target, true, true)

	local function poll(ticks)
		pools = math.max(pools, #xenos.GetActorsByType("acid-pool"), #marines.GetActorsByType("acid-pool"))
		if ticks >= 600 then
			print("TEST boiler " .. ((target.IsDead or target.Health < h0) and pools > 0 and "PASS" or "FAIL") .. " (marine " .. h0 .. " -> " .. (target.IsDead and 0 or target.Health) .. ", most acid pools " .. pools .. ")")
		else
			Trigger.AfterDelay(10, function() poll(ticks + 10) end)
		end
	end
	Trigger.AfterDelay(10, function() poll(10) end)
end
