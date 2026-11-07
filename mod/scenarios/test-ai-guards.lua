-- Scenario test: the marine bot keeps fighters beside a miner far from its base (MinerGuardBotModule in Bots.cs). Five idle
-- riflemen start at the base and a marine miner stands 30 cells away. Prints "TEST ai-guards PASS" if at least two riflemen
-- reach the miner by tick 1500 and at least two are still beside it at tick 2500, else "TEST ai-guards FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local miner = marines.GetActorsByType("miner")[1]
	local reached

	local function beside()
		local n = 0
		for _, a in ipairs(marines.GetActorsByType("rifleman")) do
			if not a.IsDead and math.abs(a.Location.X - miner.Location.X) <= 4 and math.abs(a.Location.Y - miner.Location.Y) <= 4 then
				n = n + 1
			end
		end
		return n
	end

	local function poll(ticks)
		if reported then
			return
		end
		local n = beside()
		if not reached and n >= 2 then
			reached = ticks
		end
		if ticks >= 2500 or (ticks >= 1500 and not reached) then
			reported = true
			local ok = reached ~= nil and n >= 2
			print("TEST ai-guards " .. (ok and "PASS" or "FAIL") .. " (two riflemen reached the miner at tick " .. tostring(reached or "never") ..
				", beside it at tick " .. ticks .. ": " .. n .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
