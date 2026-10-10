-- Scenario test (see mod/test_scenarios.sh): a rifleman and a Runner should fight on sight and both take damage.
-- Prints "TEST combat PASS" or "TEST combat FAIL". It polls early, because once both die the marines lose and the
-- game over stops the script clock.
local done = false

WorldLoaded = function()
	local rifleman = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	local runner = Player.GetPlayer("Xenos").GetActorsByType("runner")[1]
	local riflemanMax, runnerMax = rifleman.MaxHealth, runner.MaxHealth

	local function poll(ticks)
		if done then
			return
		end
		local riflemanHurt = rifleman.IsDead or rifleman.Health < riflemanMax
		local runnerHurt = runner.IsDead or runner.Health < runnerMax
		if riflemanHurt and runnerHurt then
			done = true
			print("TEST combat PASS (both sides took damage by tick " .. ticks .. ")")
		elseif ticks >= 300 then
			done = true
			print("TEST combat FAIL (rifleman hurt=" .. tostring(riflemanHurt) .. ", runner hurt=" .. tostring(runnerHurt) .. ")")
		else
			Trigger.AfterDelay(5, function() poll(ticks + 5) end)
		end
	end
	Trigger.AfterDelay(5, function() poll(5) end)
end
