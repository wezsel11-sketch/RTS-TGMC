-- Scenario test (see mod/test_scenarios.sh): the Skirmish AI at one strength (__LEVEL__, set by the map) builds an army
-- and sends it at the marine rifleman in the corner. It records the tick at which the first xeno unit gets within nine cells
-- of that marine. Easy waits before its first attack and sends big groups, Hard sends small ones early, so the ticks run
-- Easy > Normal > Hard. Prints "TEST ai-__LEVEL__ PASS" or "TEST ai-__LEVEL__ FAIL" with the tick and the army size then.
local Level = "__LEVEL__"
local Window = { easy = { 3500, 9500 }, normal = { 1200, 4500 }, hard = { 600, 2800 } }
local army = { "runner", "hunter", "sentinel", "drone", "warrior" }

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local marine = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	local done = false
	local function poll(tick)
		if done then
			return
		end
		local units = xenos.GetActorsByTypes(army)
		local near = false
		for _, a in ipairs(units) do
			if (a.Location - marine.Location).Length <= 9 then
				near = true
			end
		end
		if tick % 500 == 0 then
			print("STAT " .. Level .. " tick=" .. tick .. " units=" .. #units)
		end
		if near or marine.IsDead or tick >= 12000 then
			done = true
			local w = Window[Level]
			local ok = tick >= w[1] and tick <= w[2]
			print("TEST ai-" .. Level .. (ok and " PASS" or " FAIL") .. " (first xeno within nine cells at tick " .. tick
				.. ", " .. #units .. " units then; expected between " .. w[1] .. " and " .. w[2] .. ")")
			return
		end
		Trigger.AfterDelay(10, function() poll(tick + 10) end)
	end
	Trigger.AfterDelay(10, function() poll(10) end)
end
