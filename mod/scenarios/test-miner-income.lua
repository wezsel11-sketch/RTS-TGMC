-- Scenario test: a claimed marine miner pays its income. Prints the cash gained in 1000 ticks; the miner pays 12 per 50 ticks,
-- so 240 is the expected figure. "TEST miner-income PASS" when at least 200 came in.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local cash0 = marines.Cash
	Trigger.AfterDelay(1000, function()
		local gained = marines.Cash - cash0
		print("TEST miner-income " .. (gained >= 200 and "PASS" or "FAIL") .. " (gained " .. gained .. " in 1000 ticks, expected 240)")
	end)
end
