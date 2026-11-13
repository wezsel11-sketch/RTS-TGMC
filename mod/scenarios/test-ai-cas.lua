-- Scenario test: the marine AI (squads removed, every unit holding fire) calls in CAS on its own when it sees a cluster of enemies.
-- Prints "TEST ai-cas PASS" or "TEST ai-cas FAIL".
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local total = #xenos.GetActorsByType("hunter")
	-- Standing still, hunters fade from sight and the AI cannot aim at what it cannot see: switch their stealth off (as in test-ai-pod).
	-- They also hold fire: left alone they kill the one rifleman who sees them within ten seconds, and a blind AI calls no strike.
	Utils.Do(xenos.GetActorsByType("hunter"), function(h) h.UseAbility(1) h.Stance = "HoldFire" end)
	local function poll(ticks)
		if reported then
			return
		end
		local dead = total - #xenos.GetActorsByType("hunter")
		if dead >= 1 then
			reported = true
			print("TEST ai-cas PASS (" .. dead .. " of " .. total .. " hunters dead by tick " .. ticks .. ")")
		elseif ticks >= 5000 then
			reported = true
			print("TEST ai-cas FAIL (" .. dead .. " of " .. total .. " hunters dead)")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
