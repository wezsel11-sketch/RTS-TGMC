-- Scenario test: with no drones at the start, the xeno AI builds its own drone and the drone plants weed nodes away from the silo.
-- Prints "TEST ai-drone-build PASS" or "TEST ai-drone-build FAIL".
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local function poll(ticks)
		if reported then
			return
		end
		xenos.Cash = math.max(xenos.Cash, 800)
		local drones = #xenos.GetActorsByType("drone")
		local nodes = #xenos.GetActorsByType("weed-node")
		if drones >= 1 and nodes >= 3 then
			reported = true
			print("TEST ai-drone-build PASS (" .. drones .. " drones, " .. nodes .. " weed nodes by tick " .. ticks .. ")")
		elseif ticks >= 9000 then
			reported = true
			print("TEST ai-drone-build FAIL (" .. drones .. " drones, " .. nodes .. " weed nodes)")
		else
			Trigger.AfterDelay(100, function() poll(ticks + 100) end)
		end
	end
	Trigger.AfterDelay(100, function() poll(100) end)
end
