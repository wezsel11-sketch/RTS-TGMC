-- Scenario test (see mod/test_scenarios.sh): a squad leader moving across the map has its slot-1 ability queued behind the move.
-- The ability must stay ready while the leader walks and fire only when it arrives. Prints "TEST queued-ability PASS" or FAIL.
local done = false

WorldLoaded = function()
	local leader = Player.GetPlayer("Marines").GetActorsByType("squad_leader")[1]
	leader.Move(CPos.New(18, 10))

	local queued = false
	Trigger.AfterDelay(25, function()
		queued = leader.QueueAbility(1)
	end)

	local function poll(ticks)
		if done then
			return
		end
		local ready = leader.AbilityReady(1)
		if queued and not ready and leader.Location.X < 15 then
			done = true
			print("TEST queued-ability FAIL (ability fired before arrival at x " .. leader.Location.X .. ")")
		elseif queued and not ready then
			done = true
			print("TEST queued-ability PASS (ability fired on arrival at x " .. leader.Location.X .. ", tick " .. ticks .. ")")
		elseif ticks >= 1500 then
			done = true
			print("TEST queued-ability FAIL (queued=" .. tostring(queued) .. ", never fired)")
		else
			Trigger.AfterDelay(10, function() poll(ticks + 10) end)
		end
	end
	Trigger.AfterDelay(10, function() poll(10) end)
end
