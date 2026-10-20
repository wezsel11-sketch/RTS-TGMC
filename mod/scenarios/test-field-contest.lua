-- Scenario test: a xeno runner attacks an unclaimed ore field. The field must be disabled, not destroyed: after 900 ticks it
-- is still on the map at the disabled level (about 25% of 500). Prints "TEST field-contest PASS|FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local neutral = Player.GetPlayer("Neutral")
	local runner = xenos.GetActorsByType("runner")[1]
	local field = neutral.GetActorsByType("miner-field")[1]
	Trigger.AfterDelay(10, function()
		runner.Attack(field, true, true)
	end)
	Trigger.AfterDelay(900, function()
		local alive = #neutral.GetActorsByType("miner-field") == 1
		local hp = alive and neutral.GetActorsByType("miner-field")[1].Health or 0
		print("TEST field-contest " .. ((alive and hp <= 150) and "PASS" or "FAIL") .. " (field on map " .. tostring(alive) .. ", health " .. hp .. ")")
	end)
end
