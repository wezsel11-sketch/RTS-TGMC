-- Scenario test (see mod/test_scenarios.sh): a Runner hits a rifleman several times within 250 ticks. The owner must get exactly
-- one under-attack event in that window, while the rifleman is hit at least twice. Prints "TEST alert PASS" or "TEST alert FAIL".
local done = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local rifleman = marines.GetActorsByType("rifleman")[1]
	local hits, lastHealth = 0, rifleman.Health

	local function poll(ticks)
		if done then
			return
		end
		if rifleman.IsDead then
			done = true
			print("TEST alert FAIL (rifleman died after " .. hits .. " hits)")
			return
		end
		if rifleman.Health < lastHealth then
			hits = hits + 1
		end
		lastHealth = rifleman.Health
		if ticks >= 200 then
			done = true
			local alerts = marines.EventCount("event-under-attack")
			if alerts == 1 and hits >= 2 then
				print("TEST alert PASS (" .. hits .. " hits, 1 alert by tick " .. ticks .. ")")
			else
				print("TEST alert FAIL (" .. hits .. " hits, " .. alerts .. " alerts)")
			end
		else
			Trigger.AfterDelay(5, function() poll(ticks + 5) end)
		end
	end
	Trigger.AfterDelay(5, function() poll(5) end)
end
