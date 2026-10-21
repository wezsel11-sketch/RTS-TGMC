-- Scenario test: a marine Skirmish AI that starts with no engineer, beside an unclaimed ore field, must build an engineer on its own
-- (FieldWorkerBotModule in Bots.cs), send it to the field (FieldBotModule) and end up owning a miner. Prints "TEST ai-engineers PASS"
-- or "TEST ai-engineers FAIL". It polls so that it finishes as soon as the marines own a miner.
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local sawEngineer = false

	local function poll(ticks)
		if reported then
			return
		end
		if #marines.GetActorsByType("engineer") > 0 then
			sawEngineer = true
		end
		if #marines.GetActorsByType("miner") > 0 then
			reported = true
			print("TEST ai-engineers PASS (a marine miner by tick " .. ticks .. ", engineer seen " .. tostring(sawEngineer) .. ")")
		elseif ticks >= 6000 then
			reported = true
			print("TEST ai-engineers FAIL (no marine miner after " .. ticks .. " ticks, engineer seen " .. tostring(sawEngineer) .. ", cash " .. marines.Cash .. ")")
		else
			Trigger.AfterDelay(50, function() poll(ticks + 50) end)
		end
	end
	Trigger.AfterDelay(50, function() poll(50) end)
end
