-- Scenario test: an engineer repairs an ore field (MinerField). Once it is back to full health it is the engineer's
-- side's miner and the field is gone. Prints "TEST miner-field PASS" or "TEST miner-field FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local neutral = Player.GetPlayer("Neutral")
	local engineer = marines.GetActorsByType("engineer")[1]
	local field = neutral.GetActorsByType("miner-field")[1]
	Trigger.AfterDelay(10, function()
		engineer.Attack(field, true, true)
	end)
	Trigger.AfterDelay(900, function()
		local claimed = #marines.GetActorsByType("miner") == 1
		local gone = #neutral.GetActorsByType("miner-field") == 0
		print("TEST miner-field " .. ((claimed and gone) and "PASS" or "FAIL") .. " (miner for marines " .. tostring(claimed) .. ", field gone " .. tostring(gone) .. ")")
	end)
end
