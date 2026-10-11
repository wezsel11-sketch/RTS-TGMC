-- Scenario test (see mod/test_scenarios.sh): a produced unit should leave the cryo pod and walk to its rally point.
-- Prints "TEST rally PASS" or "TEST rally FAIL". It polls so that it finishes as soon as the unit arrives.
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local pod = marines.GetActorsByType("cryo-pod")[1]
	local target = CPos.New(12, 14)
	pod.RallyPoint = target

	local built
	local queued = marines.Build({ "rifleman" }, function(units)
		built = units[1]
	end)

	local function poll(ticks)
		if reported then
			return
		end
		if built ~= nil and not built.IsDead then
			local dx, dy = built.Location.X - target.X, built.Location.Y - target.Y
			if dx * dx + dy * dy <= 9 then
				reported = true
				print("TEST rally PASS (rifleman reached " .. tostring(built.Location) .. " by tick " .. ticks .. ")")
				return
			end
		end
		if ticks >= 1000 then
			reported = true
			print("TEST rally FAIL (built=" .. tostring(built ~= nil) .. ", queued=" .. tostring(queued) .. ")")
			return
		end
		Trigger.AfterDelay(25, function() poll(ticks + 25) end)
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
