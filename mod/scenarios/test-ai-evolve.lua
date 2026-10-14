-- Scenario test: the xeno AI evolves its runners into hunters when it has cash to spare. Prints "TEST ai-evolve PASS" or "TEST ai-evolve FAIL".
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local function poll(ticks)
		if reported then
			return
		end
		xenos.Cash = math.max(xenos.Cash, 1500)
		local hunters = #xenos.GetActorsByType("hunter")
		if hunters >= 1 then
			reported = true
			print("TEST ai-evolve PASS (" .. hunters .. " hunters from runners by tick " .. ticks .. ")")
		elseif ticks >= 1500 then
			reported = true
			print("TEST ai-evolve FAIL (no runner evolved)")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
