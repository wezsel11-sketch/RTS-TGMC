-- Scenario test: the xeno AI sends its drones out and plants weed nodes, so its weeds reach well past the silo. Prints "TEST ai-weeds PASS" or
-- "TEST ai-weeds FAIL" (it passes when a weed node or weeds stand 16 or more cells from the silo).
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local silo = xenos.GetActorsByType("resin-silo")[1]
	local function reach()
		local far = 0
		for _, a in ipairs(xenos.GetActorsByTypes({ "weed-node", "weeds" })) do
			local dx, dy = a.Location.X - silo.Location.X, a.Location.Y - silo.Location.Y
			far = math.max(far, math.floor(math.sqrt(dx * dx + dy * dy)))
		end
		return far
	end
	local function poll(ticks)
		if reported then
			return
		end
		xenos.Cash = math.max(xenos.Cash, 800)
		local far = reach()
		if far >= 16 then
			reported = true
			print("TEST ai-weeds PASS (weeds reach " .. far .. " cells from the silo by tick " .. ticks .. ")")
		elseif ticks >= 9000 then
			reported = true
			print("TEST ai-weeds FAIL (weeds reach only " .. far .. " cells, " .. #xenos.GetActorsByType("weed-node") .. " nodes)")
		else
			Trigger.AfterDelay(100, function() poll(ticks + 100) end)
		end
	end
	Trigger.AfterDelay(100, function() poll(100) end)
end
