-- Scenario test: the squad leader's Mark puts a sensor ping on the nearest enemy.
-- Prints "TEST squadgear PASS" or "TEST squadgear FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local leader = marines.GetActorsByType("squad_leader")[1]
	Trigger.AfterDelay(10, function()
		leader.UseAbility(3)
	end)
	Trigger.AfterDelay(120, function()
		local pings = #marines.GetActorsByType("sensor-ping")
		print("TEST squadgear " .. (pings >= 1 and "PASS" or "FAIL") .. " (" .. pings .. " pings)")
	end)
end
