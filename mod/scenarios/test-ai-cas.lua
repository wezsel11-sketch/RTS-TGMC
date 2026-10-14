-- Scenario test: the marine AI (squads removed, every unit holding fire) calls in CAS on its own when it sees a cluster of enemies.
-- Prints "TEST ai-cas PASS" or "TEST ai-cas FAIL".
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local total = #xenos.GetActorsByType("hunter")
	local function poll(ticks)
		if reported then
			return
		end
		local dead = total - #xenos.GetActorsByType("hunter")
		if dead >= 1 then
			reported = true
			print("TEST ai-cas PASS (" .. dead .. " of " .. total .. " hunters dead by tick " .. ticks .. ")")
		elseif ticks >= 5000 then
			reported = true
			print("TEST ai-cas FAIL (" .. dead .. " of " .. total .. " hunters dead)")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
