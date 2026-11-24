-- Scenario test: a marine miner is a capture point. A hunter attacks it; knocked down to its floor it is not destroyed but falls back
-- to a free ore field that belongs to no one, and the marines get no more income from it. Cash is read once the field is back, and
-- after 1000 more ticks the gain must be under 24. Prints "TEST miner-disabled-income PASS" or FAIL.
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local neutral = Player.GetPlayer("Neutral")
	local miner = marines.GetActorsByType("miner")[1]
	local hunter = xenos.GetActorsByType("hunter")[1]
	local fields0 = #neutral.GetActorsByType("miner-field")
	hunter.Attack(miner, true, true)

	local function poll(ticks)
		if reported then
			return
		end
		local fields = #neutral.GetActorsByType("miner-field")
		if fields > fields0 and #marines.GetActorsByType("miner") == 0 then
			reported = true
			local cash0 = marines.Cash
			Trigger.AfterDelay(1000, function()
				local gained = marines.Cash - cash0
				local still = #neutral.GetActorsByType("miner-field") > fields0
				print("TEST miner-disabled-income " .. ((still and gained < 24) and "PASS" or "FAIL") .. " (free field " .. tostring(still) ..
					", gained " .. gained .. " in 1000 ticks, fell by tick " .. ticks .. ")")
			end)
			return
		end
		if ticks >= 6000 then
			reported = true
			print("TEST miner-disabled-income FAIL (miner never fell back to a field by tick " .. ticks .. ", miners " ..
				#marines.GetActorsByType("miner") .. ", fields " .. fields .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
