-- Scenario test (see mod/test_scenarios.sh): with repeat build on, a cryo pod keeps making riflemen until repeat is turned off.
-- Prints "TEST repeat PASS" or "TEST repeat FAIL".
local done = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	marines.Cash = 5000
	marines.SetRepeat(true)
	Trigger.AfterDelay(10, function()
		marines.QueueUnit("rifleman")
	end)

	local function count()
		return #marines.GetActorsByType("rifleman")
	end

	local function poll(ticks)
		if done then
			return
		end
		if count() >= 2 then
			marines.SetRepeat(false)
			local atOff = count()
			Trigger.AfterDelay(1200, function()
				done = true
				local after = count()
				if after <= atOff + 1 then
					print("TEST repeat PASS (" .. atOff .. " built with repeat on, " .. after .. " after it was turned off)")
				else
					print("TEST repeat FAIL (kept building after repeat off: " .. atOff .. " -> " .. after .. ")")
				end
			end)
		elseif ticks >= 2400 then
			done = true
			print("TEST repeat FAIL (only " .. count() .. " built with repeat on)")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
