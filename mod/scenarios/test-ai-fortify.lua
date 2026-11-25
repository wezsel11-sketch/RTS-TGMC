-- Scenario test: the xeno bot fortifies the undecoded disk terminals with no marines near them. By tick 4000 each of the two terminals
-- has at least 2 xeno fighters within 3 cells, and at least one resin turret stands within 5 cells of a terminal.
-- Prints "TEST ai-fortify PASS" or "TEST ai-fortify FAIL".
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local terminals = {}
	for _, a in ipairs(Map.ActorsInWorld) do
		if a.Type == "disk-terminal" then terminals[#terminals + 1] = a end
	end

	local function near(t, types, cells)
		local n = 0
		for _, a in ipairs(xenos.GetActorsByTypes(types)) do
			if not a.IsDead and math.max(math.abs(a.Location.X - t.Location.X), math.abs(a.Location.Y - t.Location.Y)) <= cells then
				n = n + 1
			end
		end
		return n
	end

	local function check(tick)
		local guarded, turrets, why = true, 0, ""
		for _, t in ipairs(terminals) do
			local g = near(t, { "runner" }, 3)
			why = why .. string.format("terminal %d,%d: %d guards, %d turrets; ", t.Location.X, t.Location.Y, g, near(t, { "resin-turret" }, 5))
			if g < 2 then guarded = false end
			turrets = turrets + near(t, { "resin-turret" }, 5)
		end
		if guarded and turrets > 0 then
			print("TEST ai-fortify PASS (tick " .. tick .. ": " .. why .. ")")
		elseif tick >= 4000 then
			print("TEST ai-fortify FAIL (tick 4000: " .. why .. ")")
		else
			Trigger.AfterDelay(50, function() check(tick + 50) end)
		end
	end

	check(0)
end
