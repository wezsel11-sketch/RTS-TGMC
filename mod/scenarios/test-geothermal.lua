-- Scenario test: TGMC's geothermal generators. An engineer repairs one into a running generator (Marines'); a drone corrupts
-- another for the hive. Prints "TEST geothermal PASS" or "TEST geothermal FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local engineer = marines.GetActorsByType("engineer")[1]
	local drone = xenos.GetActorsByType("drone")[1]
	local fields = Player.GetPlayer("Neutral").GetActorsByType("geothermal-field")
	local near = function(a, list)
		local best, bestd = nil, 99999
		for _, f in ipairs(list) do
			local d = math.abs(f.Location.X - a.Location.X) + math.abs(f.Location.Y - a.Location.Y)
			if d < bestd then best, bestd = f, d end
		end
		return best
	end
	Trigger.AfterDelay(10, function()
		engineer.Attack(near(engineer, fields), true, false)
		drone.Attack(near(drone, fields), true, true)
	end)
	Trigger.AfterDelay(1500, function()
		local up = #marines.GetActorsByType("geothermal")
		local corrupted = #xenos.GetActorsByType("corrupted-geothermal")
		print("TEST geothermal " .. ((up == 1 and corrupted == 1) and "PASS" or "FAIL") .. " (running " .. up .. ", corrupted " .. corrupted .. ")")
	end)
end
