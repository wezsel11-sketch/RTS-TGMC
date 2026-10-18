-- Scenario test (see mod/test_scenarios.sh): with repeat on and cash for one rifleman only, the repeat waits and nothing is built on credit.
-- Prints "TEST repeat-broke PASS" or "TEST repeat-broke FAIL".
local done = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	marines.Cash = 100
	marines.SetRepeat(true)
	Trigger.AfterDelay(10, function()
		marines.QueueUnit("rifleman")
	end)

	local function poll(ticks)
		if done then
			return
		end
		if ticks >= 2400 then
			done = true
			local built = #marines.GetActorsByType("rifleman")
			if built == 1 and marines.Cash >= 0 then
				print("TEST repeat-broke PASS (one built, repeat waited with cash " .. marines.Cash .. ")")
			else
				print("TEST repeat-broke FAIL (" .. built .. " built, cash " .. marines.Cash .. ")")
			end
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
