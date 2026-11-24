-- Scenario test: the xeno AI, with no marines, never claws a free ore field. Its drones may corrupt one (the field then turns
-- into a corrupted miner and leaves the world, which is fine); what must not happen is a field losing health.
-- Prints "TEST ai-fields PASS" when no field is hurt by 6000 ticks, "TEST ai-fields FAIL" if one is.
local reported = false

WorldLoaded = function()
	local neutral = Player.GetPlayer("Neutral")
	local fields = neutral.GetActorsByType("miner-field")
	local start = {}
	for i, f in ipairs(fields) do
		start[i] = f.Health
	end
	local function poll(ticks)
		if reported then
			return
		end
		for i, f in ipairs(fields) do
			if f.IsInWorld and not f.IsDead and f.Health < start[i] then
				reported = true
				print("TEST ai-fields FAIL (dormant field " .. i .. " was hit by tick " .. ticks .. ")")
				return
			end
		end
		if ticks >= 6000 then
			reported = true
			print("TEST ai-fields PASS (no dormant field hit by tick " .. ticks .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
