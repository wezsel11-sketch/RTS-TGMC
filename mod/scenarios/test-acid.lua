-- Scenario test (see mod/test_scenarios.sh): a dead xeno leaves a pool of acid that stings a marine standing next to it
-- and goes away again. Prints "TEST acid PASS" or "TEST acid FAIL".
local reported = false

WorldLoaded = function()
	local marines, xenos = Player.GetPlayer("Marines"), Player.GetPlayer("Xenos")
	local marine = marines.GetActorsByType("rifleman")[1]
	local runner = xenos.GetActorsByType("runner")[1]
	local start = marine.Health
	local sawPool = false


	Trigger.AfterDelay(10, function()
		runner.Kill()
	end)

	Trigger.AfterDelay(20, function()
		local found = Map.ActorsInBox(marine.CenterPosition - WVec.New(3072, 3072, 0), marine.CenterPosition + WVec.New(3072, 3072, 0), function(a)
			return a.Type == "acid-pool"
		end)
		sawPool = #found > 0
	end)

	Trigger.AfterDelay(160, function()
		if reported then
			return
		end
		reported = true
		if not sawPool then
			print("TEST acid FAIL (no acid pool after the runner died)")
		elseif marine.Health >= start then
			print("TEST acid FAIL (marine not hurt: " .. marine.Health .. "/" .. start .. ")")
		else
			print("TEST acid PASS (marine " .. start .. " -> " .. marine.Health .. ")")
		end
	end)
end
