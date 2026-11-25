-- Scenario test: ObjectiveBotModule on the contesting side. The xeno bot has six idle runners at its silo; a marine rifleman (no bot)
-- stands at the one disk terminal (20,20). The bot must send its group there: a runner comes within 3 cells of the terminal by tick
-- 2500. Prints "TEST ai-distress-contest PASS" or "TEST ai-distress-contest FAIL".
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local terminal = Map.ActorsInWorld[1]
	for _, a in ipairs(Map.ActorsInWorld) do
		if a.Type == "disk-terminal" then terminal = a end
	end

	local function report(ok, why)
		if not reported then
			reported = true
			print("TEST ai-distress-contest " .. (ok and "PASS" or "FAIL") .. " (" .. why .. ")")
		end
	end

	local function check(tick)
		for _, r in ipairs(xenos.GetActorsByType("runner")) do
			if not r.IsDead and math.max(math.abs(r.Location.X - terminal.Location.X), math.abs(r.Location.Y - terminal.Location.Y)) <= 3 then
				report(true, "a runner at the terminal by tick " .. tick)
				return
			end
		end
		if tick >= 2500 then
			report(false, "no runner within 3 cells of the terminal by tick 2500")
		else
			Trigger.AfterDelay(50, function() check(tick + 50) end)
		end
	end

	check(0)
end
