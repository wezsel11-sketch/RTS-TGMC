-- Scenario test: the marine AI calls a drop pod on a cluster of hunters by itself, and the marines inside step out. Prints "TEST ai-pod PASS" or "TEST ai-pod FAIL".
local reported = false
local peakRiflemen, peakMedics = 0, 0
-- The most riflemen seen by the hunters at once.
local jump = 0

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	-- Standing still, hunters fade from sight and the AI cannot aim at what it cannot see: switch their stealth off.
	Utils.Do(Player.GetPlayer("Xenos").GetActorsByType("hunter"), function(h) h.UseAbility(1) end)
	local function poll(ticks)
		if reported then
			return
		end
		-- Peak counts: the hunters can kill the pod's marines between two polls, so a drop that happened still counts.
		-- Riflemen standing by the hunters came by pod: the factory's step out at the base, 16 cells away (the rifleman watching the
		-- hunters stands 7 cells off, outside this count).
		local near = 0
		for _, r in ipairs(marines.GetActorsByType("rifleman")) do
			if not r.IsDead and math.abs(r.Location.X - 22) <= 5 and math.abs(r.Location.Y - 23) <= 5 then
				near = near + 1
			end
		end
		jump = math.max(jump, near)
		peakRiflemen = math.max(peakRiflemen, #marines.GetActorsByType("rifleman"))
		peakMedics = math.max(peakMedics, #marines.GetActorsByType("medic"))
		local riflemen, medics = peakRiflemen, peakMedics
		if jump >= 3 then
			reported = true
			print("TEST ai-pod PASS (" .. jump .. " pod riflemen by the hunters by tick " .. ticks .. ")")
		elseif ticks >= 2500 then
			reported = true
			print("TEST ai-pod FAIL (at most " .. jump .. " riflemen by the hunters, peak " .. riflemen .. " riflemen, " .. medics .. " medics)")
		else
			Trigger.AfterDelay(5, function() poll(ticks + 5) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
