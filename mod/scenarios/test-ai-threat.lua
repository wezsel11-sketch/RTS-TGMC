-- Scenario test: ThreatMemory (tgmc/code/ThreatMemory.cs). The marines have seen nothing near three xeno sentinels, so the
-- threat there is 0. A rifleman is put beside them, so it is seen and above 0. The rifleman leaves: the memory outlives sight
-- (still above 0 five samples later) and fades (below half its peak within 40 samples).
-- Prints "TEST ai-threat PASS" or "TEST ai-threat FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local scout = marines.GetActorsByType("rifleman")[1]
	local spot = CPos.New(30, 24)
	local function threat() return marines.ThreatNear(spot, 3) end
	local function report(ok, why)
		if not reported then
			reported = true
			print("TEST ai-threat " .. (ok and "PASS" or "FAIL") .. " (" .. why .. ")")
		end
	end

	Trigger.AfterDelay(50, function()
		local unseen = threat()
		if unseen ~= 0 then
			report(false, "threat " .. unseen .. " before anything was seen")
			return
		end
		scout.Teleport(CPos.New(28, 24))
		Trigger.AfterDelay(100, function()
			local peak = threat()
			if peak <= 0 then
				report(false, "threat still 0 with the sentinels in sight")
				return
			end
			scout.Teleport(CPos.New(8, 8))
			local function sample(k)
				local t = threat()
				if k <= 5 and t <= 0 then
					report(false, "forgotten after " .. k .. " samples")
				elseif t * 2 < peak then
					report(k > 5, "peak " .. peak .. ", below half after " .. k .. " samples")
				elseif k >= 40 then
					report(false, "peak " .. peak .. ", still " .. t .. " after 40 samples")
				else
					Trigger.AfterDelay(25, function() sample(k + 1) end)
				end
			end
			Trigger.AfterDelay(25, function() sample(1) end)
		end)
	end)
end
