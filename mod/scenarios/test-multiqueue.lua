-- Scenario test: with two production buildings the unit queue builds two marines at the same time, so both queued riflemen come out
-- together instead of one after the other. Prints "TEST multiqueue PASS" or "TEST multiqueue FAIL".
local ticks = 0
local done = {}

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local before = #marines.GetActorsByType("rifleman")

	-- The unit queue wakes up on the first tick, so ask for the builds a moment after the world loads.
	Trigger.AfterDelay(5, function()
		marines.QueueUnit("rifleman")
		marines.QueueUnit("rifleman")
	end)

	local function tick()
		ticks = ticks + 5
		if ticks % 250 == 0 then
			print("STAT tick " .. ticks .. " cash " .. marines.Cash .. " riflemen " .. #marines.GetActorsByType("rifleman"))
		end
		local count = #marines.GetActorsByType("rifleman") - before
		while #done < count do
			table.insert(done, ticks)
		end
		if #done >= 2 then
			local gap = done[2] - done[1]
			print("TEST multiqueue " .. (gap <= 25 and "PASS" or "FAIL") .. " (done at ticks " .. done[1] .. " and " .. done[2] .. ", gap " .. gap .. ")")
		elseif ticks >= 2500 then
			print("TEST multiqueue FAIL (only " .. #done .. " built after " .. ticks .. " ticks)")
		else
			Trigger.AfterDelay(5, tick)
		end
	end
	Trigger.AfterDelay(5, tick)
end
