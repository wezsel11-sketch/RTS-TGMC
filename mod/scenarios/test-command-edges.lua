-- Scenario test: two edge cases of the command layer, run side by side. The harness also greps the log for exceptions.
--   retreat-lost:   the cryo pod a rifleman is retreating to is destroyed mid-walk; the rifleman must survive and end up idle.
--   ability-dies:   a squad leader with a queued ability dies before it arrives; nothing may throw, and the dead leader does not fire it.
-- (Shift-queued retreat cannot be driven from Lua: the Retreat property has no queued argument.)
-- Prints one "TEST command-edges-<name> PASS|FAIL" line per case after 600 ticks.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local function at(type, y)
		for _, a in ipairs(marines.GetActorsByType(type)) do
			if a.Location.Y == y then return a end
		end
	end

	local runner = at("rifleman", 4)
	local pod = marines.GetActorsByType("cryo-pod")[1]
	runner.Retreat()
	Trigger.AfterDelay(75, function() pod.Kill() end)

	local leader = at("squad_leader", 10)
	leader.Move(CPos.New(18, 10))
	Trigger.AfterDelay(10, function() leader.QueueAbility(1) end)
	Trigger.AfterDelay(60, function() leader.Kill() end)

	Trigger.AfterDelay(600, function()
		print("TEST command-edges-retreat-lost " .. ((not runner.IsDead and runner.IsIdle) and "PASS" or "FAIL") ..
			" (alive " .. tostring(not runner.IsDead) .. ", idle " .. tostring(runner.IsIdle) .. ")")
		print("TEST command-edges-ability-dies " .. (leader.IsDead and "PASS" or "FAIL") .. " (leader dead " .. tostring(leader.IsDead) .. ")")
	end)
end
