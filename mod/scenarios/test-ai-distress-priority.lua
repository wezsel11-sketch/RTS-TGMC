-- Scenario test: the contesting side's ObjectiveBotModule picks the terminal being decoded. Three marine riflemen idle five cells from
-- the terminal at (20,8), outside its hold circle; one rifleman decodes the terminal at (20,32). The xeno bot's runners must reach the
-- decoded one (within 3 cells, by tick 2500) and none may reach the other first.
-- Prints "TEST ai-distress-priority PASS" or "TEST ai-distress-priority FAIL".
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local idle, decoding
	for _, a in ipairs(Map.ActorsInWorld) do
		if a.Type == "disk-terminal" then
			if a.Location.Y < 20 then idle = a else decoding = a end
		end
	end

	local function report(ok, why)
		if not reported then
			reported = true
			print("TEST ai-distress-priority " .. (ok and "PASS" or "FAIL") .. " (" .. why .. ")")
		end
	end

	local function at(t)
		for _, r in ipairs(xenos.GetActorsByType("runner")) do
			if not r.IsDead and math.max(math.abs(r.Location.X - t.Location.X), math.abs(r.Location.Y - t.Location.Y)) <= 3 then
				return true
			end
		end
		return false
	end

	local function check(tick)
		if at(idle) then
			report(false, "a runner went to the terminal nobody decodes, tick " .. tick)
		elseif at(decoding) then
			report(true, "a runner at the terminal being decoded by tick " .. tick)
		elseif tick >= 2500 then
			report(false, "no runner at the terminal being decoded by tick 2500")
		else
			Trigger.AfterDelay(25, function() check(tick + 25) end)
		end
	end

	check(0)
end
