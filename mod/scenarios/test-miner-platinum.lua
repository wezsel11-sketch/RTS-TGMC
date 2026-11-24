-- Scenario test: a miner on a platinum vein pays half as much again: 15 per 50 ticks, so 300 in 1000 ticks against a plain
-- miner's 200. "TEST miner-platinum PASS" when between 270 and 330 came in.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local cash0 = marines.Cash
	Trigger.AfterDelay(1000, function()
		local gained = marines.Cash - cash0
		print("TEST miner-platinum " .. ((gained >= 270 and gained <= 330) and "PASS" or "FAIL") .. " (gained " .. gained .. " in 1000 ticks, expected 300)")
	end)
end
