-- Scenario test: a runner claws a marine miner over and over. The marines get exactly one miner-under-attack warning in the
-- first 200 ticks (the cooldown stops a flood), and the miner was hit at least twice. Prints "TEST raid-warning PASS|FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local miner = marines.GetActorsByType("miner")[1]
	local runner = Player.GetPlayer("Xenos").GetActorsByType("runner")[1]
	local hits, last = 0, miner.Health
	Trigger.AfterDelay(10, function() runner.Attack(miner, true, true) end)
	local function poll(ticks)
		if miner.Health < last then hits = hits + 1 end
		last = miner.Health
		if ticks < 200 then
			Trigger.AfterDelay(5, function() poll(ticks + 5) end)
			return
		end
		local warnings = marines.EventCount("event-miner-under-attack")
		print("TEST raid-warning " .. ((warnings == 1 and hits >= 2) and "PASS" or "FAIL") .. " (" .. hits .. " hits, " .. warnings .. " warnings)")
	end
	poll(0)
end
