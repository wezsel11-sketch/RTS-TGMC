-- Scenario test: a destroyed vehicle leaves its wreck (SpawnActorOnDeath on each vehicle, the <vehicle>-wreck actors in units.yaml).
-- The tank, APC and SOM tank are killed at tick 10. Five ticks later each has a wreck on its cell, owned by no side; the wrecks
-- burn out after a while and are gone by tick 1600. Prints "TEST vehicle-wrecks PASS" or "TEST vehicle-wrecks FAIL" with what failed.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local neutral = Player.GetPlayer("Neutral")
	local types = { "tank", "apc", "som-tank" }
	local cells, bad = {}, {}
	Trigger.AfterDelay(10, function()
		for _, t in ipairs(types) do
			local v = marines.GetActorsByType(t)[1]
			cells[t] = v.Location
			v.Kill()
		end
	end)
	Trigger.AfterDelay(15, function()
		for _, t in ipairs(types) do
			local w = neutral.GetActorsByType(t .. "-wreck")[1]
			if not w then
				table.insert(bad, t .. " left no wreck")
			elseif w.Location ~= cells[t] then
				table.insert(bad, t .. "'s wreck is off its cell")
			end
		end
	end)
	Trigger.AfterDelay(1600, function()
		for _, t in ipairs(types) do
			if #neutral.GetActorsByType(t .. "-wreck") > 0 then table.insert(bad, t .. "'s wreck never burnt out") end
		end
		print("TEST vehicle-wrecks " .. (#bad == 0 and "PASS" or "FAIL (" .. table.concat(bad, "; ") .. ")"))
	end)
end
