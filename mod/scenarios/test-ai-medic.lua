-- Scenario test: the marine AI sends an idle medic to a wounded marine, who is healed. Prints "TEST ai-medic PASS" or "TEST ai-medic FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local patient = marines.GetActorsByType("rifleman")[1]
	patient.Health = 40
	local function poll(ticks)
		if reported then
			return
		end
		if patient.Health > 40 then
			reported = true
			print("TEST ai-medic PASS (healed to " .. patient.Health .. " by tick " .. ticks .. ")")
		elseif ticks >= 1500 then
			reported = true
			print("TEST ai-medic FAIL (patient still at " .. patient.Health .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
