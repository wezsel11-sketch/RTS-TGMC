-- Scenario test: the xeno AI, with no marines, leaves the dormant ore fields alone. A field only becomes a target once a marine
-- has repaired it (claimed), so with no marines every field keeps its starting health and none falls.
-- Prints "TEST ai-fields PASS" when no field is touched by 6000 ticks, "TEST ai-fields FAIL" if one is hit.
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
			if f.IsDead or not f.IsInWorld or f.Health < start[i] then
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
