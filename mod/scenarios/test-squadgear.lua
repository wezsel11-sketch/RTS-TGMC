-- Scenario test: the squad leader's Mirage drops a decoy in front of him, and his Mark puts a sensor ping on the nearest enemy.
-- Prints "TEST squadgear PASS" or "TEST squadgear FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local leader = marines.GetActorsByType("squad_leader")[1]
	Trigger.AfterDelay(10, function()
		leader.UseAbility(2)
		leader.UseAbility(3)
	end)
	Trigger.AfterDelay(120, function()
		local decoys = #marines.GetActorsByType("mirage-decoy")
		local pings = #marines.GetActorsByType("sensor-ping")
		print("TEST squadgear " .. ((decoys >= 1 and pings >= 1) and "PASS" or "FAIL") .. " (" .. decoys .. " decoys, " .. pings .. " pings)")
	end)
end
