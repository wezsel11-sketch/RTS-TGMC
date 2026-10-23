-- Scenario test: the marine AI calls a drop pod on a cluster of hunters by itself, and the marines inside step out. Prints "TEST ai-pod PASS" or "TEST ai-pod FAIL".
local reported = false
local peakRiflemen, peakMedics = 0, 0

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local function poll(ticks)
		if reported then
			return
		end
		-- Peak counts: the hunters can kill the pod's marines between two polls, so a drop that happened still counts.
		peakRiflemen = math.max(peakRiflemen, #marines.GetActorsByType("rifleman"))
		peakMedics = math.max(peakMedics, #marines.GetActorsByType("medic"))
		local riflemen, medics = peakRiflemen, peakMedics
		if riflemen >= 4 and medics >= 1 then
			reported = true
			print("TEST ai-pod PASS (" .. riflemen .. " riflemen and " .. medics .. " medic by tick " .. ticks .. ")")
		elseif ticks >= 2500 then
			reported = true
			print("TEST ai-pod FAIL (" .. riflemen .. " riflemen, " .. medics .. " medics)")
		else
			Trigger.AfterDelay(5, function() poll(ticks + 5) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
