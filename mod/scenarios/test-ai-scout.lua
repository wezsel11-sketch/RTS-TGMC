-- Scenario test: on Hard, the AI sends an idle unit out to explore. Prints "TEST ai-scout PASS" or "TEST ai-scout FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local scout = marines.GetActorsByType("rifleman")[1]
	local function poll(ticks)
		if reported then
			return
		end
		if scout.Location.X >= 28 or scout.Location.Y >= 24 then
			reported = true
			print("TEST ai-scout PASS (reached " .. scout.Location.X .. "," .. scout.Location.Y .. " by tick " .. ticks .. ")")
		elseif ticks >= 2500 then
			reported = true
			print("TEST ai-scout FAIL (still at " .. scout.Location.X .. "," .. scout.Location.Y .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
