-- Scenario test: a hugger egg opens when a marine walks near it and a facehugger hops out.
-- Prints "TEST egg PASS" or "TEST egg FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local host = marines.GetActorsByType("rifleman")[1]
	host.Stance = "HoldFire"
	local seen = false
	local function watch(ticks)
		if #xenos.GetActorsByType("facehugger") > 0 then
			seen = true
		end
		if ticks > 0 then
			Trigger.AfterDelay(4, function() watch(ticks - 4) end)
		end
	end
	watch(400)
	Trigger.AfterDelay(420, function()
		print("TEST egg " .. (seen and "PASS" or "FAIL") .. " (a facehugger hatched: " .. tostring(seen) .. ")")
	end)
end
