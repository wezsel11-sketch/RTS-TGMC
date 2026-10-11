-- Scenario test (see mod/test_scenarios.sh): a unit ranks up (here by script, and by killing), and a ranked unit hits harder.
-- Prints "TEST vet PASS" or "TEST vet FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local runner = Player.GetPlayer("Xenos").GetActorsByType("runner")[1]
	local victim = marines.GetActorsByType("rifleman")[1]
	local spare = marines.GetActorsByType("rifleman")[2]
	local scripted = marines.GetActorsByType("rifleman")[3]

	scripted.GiveLevels(2, true)
	local scriptedLevel = scripted.Level

	-- A runner (cost 50) ranks up at 150% of its cost: killing one rifleman (worth 100) is enough
	victim.Health = 1
	runner.Stop()

	local function poll(ticks)
		if runner.Level >= 1 then
			print("TEST vet PASS (scripted rifleman at rank " .. scriptedLevel .. ", the runner reached rank " .. runner.Level .. " by killing at tick " .. ticks .. ")")
		elseif ticks >= 400 then
			print("TEST vet FAIL (scripted rank " .. scriptedLevel .. ", runner rank " .. runner.Level .. ", victim dead=" .. tostring(victim.IsDead) .. ")")
		else
			Trigger.AfterDelay(5, function() poll(ticks + 5) end)
		end
	end
	if scriptedLevel ~= 2 then
		print("TEST vet FAIL (GiveLevels(2) left the rifleman at rank " .. scriptedLevel .. ")")
		return
	end
	runner.Attack(victim)
	Trigger.AfterDelay(5, function() poll(5) end)
end
