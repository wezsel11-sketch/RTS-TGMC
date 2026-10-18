-- Scenario test (see mod/test_scenarios.sh): an orbital strike needs no jet and still hurts the target. A runner stands on the spot the
-- Lua call strikes; it must lose health soon after the call. Prints "TEST orbital-nojet PASS" or "TEST orbital-nojet FAIL".
local done = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local runner = Player.GetPlayer("Xenos").GetActorsByType("runner")[1]
	local depot = marines.GetActorsByType("workshop")[1]
	local max = runner.MaxHealth
	Trigger.AfterDelay(10, function()
		depot.ActivateCondorStrike(CPos.New(14, 10), "orbital")
	end)

	local function poll(ticks)
		if done then
			return
		end
		if runner.IsDead or runner.Health < max then
			done = true
			print("TEST orbital-nojet PASS (target hit without a jet, by tick " .. ticks .. ")")
		elseif ticks >= 300 then
			done = true
			print("TEST orbital-nojet FAIL (target untouched after 300 ticks)")
		else
			Trigger.AfterDelay(5, function() poll(ticks + 5) end)
		end
	end
	Trigger.AfterDelay(5, function() poll(5) end)
end
