-- Scenario test: the squad leader's third ability (Mark, slot 3) can be used: a sensor ping appears on the runner it marks.
-- Prints "TEST card-slots PASS" or "TEST card-slots FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local leader = marines.GetActorsByType("squad_leader")[1]
	xenos.GetActorsByType("runner")[1].Stance = "HoldFire"
	local used = false
	Trigger.AfterDelay(10, function()
		used = leader.UseAbility(3)
	end)
	Trigger.AfterDelay(20, function()
		local pings = #Utils.Where(Map.ActorsInWorld, function(a) return a.Type == "sensor-ping" end)
		print("TEST card-slots " .. ((used and pings >= 1) and "PASS" or "FAIL") .. " (used=" .. tostring(used) .. ", pings=" .. pings .. ")")
	end)
end
