-- Scenario test: the xeno AI uses its hive powers by itself: Psychic Cure heals its wounded hunters and Call of the Burrowed brings up runners.
-- Prints "TEST hive-powers PASS" or "TEST hive-powers FAIL".
local reported = false
-- Remembered, not sampled: the AI evolves called runners into other castes within seconds, and a cured hunter can be hurt again.
local everHealed, peakRunners = false, 0

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local hunters = xenos.GetActorsByType("hunter")
	for _, h in ipairs(hunters) do
		h.Health = 60
	end
	local function poll(ticks)
		if reported then
			return
		end
		local healed = false
		for _, h in ipairs(hunters) do
			if not h.IsDead and h.Health > 100 then
				healed = true
			end
		end
		everHealed = everHealed or healed
		peakRunners = math.max(peakRunners, #xenos.GetActorsByType("runner"))
		local runners = peakRunners
		healed = everHealed
		if healed and runners >= 3 then
			reported = true
			print("TEST hive-powers PASS (cured, " .. runners .. " runners called by tick " .. ticks .. ")")
		elseif ticks >= 4500 then
			reported = true
			print("TEST hive-powers FAIL (healed=" .. tostring(healed) .. ", runners " .. runners .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
