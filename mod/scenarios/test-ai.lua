-- Scenario test (see mod/test_scenarios.sh): the Skirmish AI, set on the xeno player by the map, should spend its cash on
-- units from its silo. Prints "TEST ai PASS" or "TEST ai FAIL". It polls so that it finishes as soon as three exist.
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local army = { "runner", "hunter", "sentinel", "facehugger" }

	local function poll(ticks)
		if reported then
			return
		end
		local count = #xenos.GetActorsByTypes(army)
		if count >= 3 then
			reported = true
			print("TEST ai PASS (" .. count .. " xeno units by tick " .. ticks .. ", cash " .. xenos.Cash .. ")")
		elseif ticks >= 1000 then
			reported = true
			print("TEST ai FAIL (" .. count .. " xeno units after " .. ticks .. " ticks, cash " .. xenos.Cash .. ")")
		else
			Trigger.AfterDelay(50, function() poll(ticks + 50) end)
		end
	end
	Trigger.AfterDelay(50, function() poll(50) end)
end
