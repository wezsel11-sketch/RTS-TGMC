-- Scenario test (see mod/test_scenarios.sh): a rifleman ordered to retreat walks to the friendly cryo pod.
-- Prints "TEST retreat PASS" or "TEST retreat FAIL".
local done = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local rifleman = marines.GetActorsByType("rifleman")[1]
	local pod = marines.GetActorsByType("cryo-pod")[1]

	local accepted = rifleman.Retreat()

	local function poll(ticks)
		if done then
			return
		end
		local dx, dy = rifleman.Location.X - pod.Location.X, rifleman.Location.Y - pod.Location.Y
		if accepted and math.abs(dx) <= 1 and math.abs(dy) <= 1 then
			done = true
			print("TEST retreat PASS (reached the cryo pod by tick " .. ticks .. ")")
		elseif ticks >= 1500 then
			done = true
			print("TEST retreat FAIL (accepted=" .. tostring(accepted) .. ", at " .. rifleman.Location.X .. "," .. rifleman.Location.Y .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
