-- Scenario test: the only producer is destroyed while a unit is being built, with repeat build on. The game must carry on without a Lua
-- or engine exception (the harness greps for them), and the queue must not keep making units out of a dead building: at most the one in
-- progress finishes. Prints "TEST producer-lost PASS" or "TEST producer-lost FAIL".
local done = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local pod = marines.GetActorsByType("cryo-pod")[1]
	marines.Cash = 5000
	marines.SetRepeat(true)
	Trigger.AfterDelay(10, function()
		marines.QueueUnit("rifleman")
	end)
	-- Early enough that the first rifleman is still in the queue.
	Trigger.AfterDelay(40, function()
		pod.Kill()
	end)
	Trigger.AfterDelay(1500, function()
		done = true
		local built = #marines.GetActorsByType("rifleman")
		print("TEST producer-lost " .. (built <= 1 and "PASS" or "FAIL") .. " (" .. built .. " riflemen after the producer was destroyed, at most 1 expected)")
	end)
end
