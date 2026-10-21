-- Scenario test: retreat for SOM and for the xenos (test-retreat covers the marine rifleman). A SOM trooper must walk to the cryo pod and a
-- runner to the resin silo. Prints "TEST retreat-factions PASS" or "TEST retreat-factions FAIL".
local done = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local som = marines.GetActorsByType("som_trooper")[1]
	local pod = marines.GetActorsByType("cryo-pod")[1]
	local runner = xenos.GetActorsByType("runner")[1]
	local silo = xenos.GetActorsByType("resin-silo")[1]

	local somOk, runnerOk = som.Retreat(), runner.Retreat()

	local function near(a, b, r)
		return math.abs(a.Location.X - b.Location.X) <= r and math.abs(a.Location.Y - b.Location.Y) <= r
	end

	local function poll(ticks)
		if done then
			return
		end
		local somThere, runnerThere = near(som, pod, 1), near(runner, silo, 2)
		if somOk and runnerOk and somThere and runnerThere then
			done = true
			print("TEST retreat-factions PASS (SOM at the pod and runner at the silo by tick " .. ticks .. ")")
		elseif ticks >= 1500 then
			done = true
			print("TEST retreat-factions FAIL (SOM accepted " .. tostring(somOk) .. " there " .. tostring(somThere) ..
				", runner accepted " .. tostring(runnerOk) .. " there " .. tostring(runnerThere) .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
