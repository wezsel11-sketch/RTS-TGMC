-- Scenario test: a badly wounded marine far from the medbay is pulled back toward it by the AI. Prints "TEST ai-retreat PASS" or "TEST ai-retreat FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local patient = marines.GetActorsByType("rifleman")[1]
	local start = patient.Location.X
	patient.Health = 20
	local function poll(ticks)
		if reported then
			return
		end
		if patient.Location.X <= start - 10 then
			reported = true
			print("TEST ai-retreat PASS (walked from x " .. start .. " to " .. patient.Location.X .. " by tick " .. ticks .. ")")
		elseif ticks >= 1500 then
			reported = true
			print("TEST ai-retreat FAIL (still at x " .. patient.Location.X .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
