-- Scenario test: with a unit builder that trains only riflemen, the marine AI still gets flamers, machine gunners or smartgunners once it
-- sees a swarm of hunters: the counter-pick module asks for them. Prints "TEST ai-counter PASS" or "TEST ai-counter FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local function poll(ticks)
		if reported then
			return
		end
		marines.Cash = math.max(marines.Cash, 1500)
		local counters = #marines.GetActorsByTypes({ "flamer", "machinegunner", "smartgunner", "grenadier" })
		if counters >= 1 then
			reported = true
			print("TEST ai-counter PASS (" .. counters .. " counter units by tick " .. ticks .. ")")
		elseif ticks >= 3000 then
			reported = true
			print("TEST ai-counter FAIL (no counter unit, riflemen " .. #marines.GetActorsByType("rifleman") .. ")")
		else
			Trigger.AfterDelay(50, function() poll(ticks + 50) end)
		end
	end
	Trigger.AfterDelay(50, function() poll(50) end)
end
