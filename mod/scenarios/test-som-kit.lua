-- Scenario test: the SOM's own tools (the human player is SOM).
-- Heat: a runner shot by an Infantryman keeps losing health after the shooting stops (it burns).
-- Recall: the Blink Assault Veteran teleports to the beacon from across the map.
-- Beacon pod: a drop pod called beside the beacon brings six Infantrymen in place of four.
-- Prints "TEST som-kit PASS" or "TEST som-kit FAIL (what failed)".
WorldLoaded = function()
	local som = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local bad = {}
	local runner = xenos.GetActorsByType("runner")[1]
	runner.Stance = "HoldFire"
	local shooter = som.GetActorsByType("som_trooper")[1]
	local blade = som.GetActorsByType("som_blademan")[1]
	blade.Stance = "HoldFire"
	local beacon = som.GetActorsByType("som-beacon")[1]
	local pod = som.GetActorsByType("cryo-pod")[1]
	local troopers0 = #som.GetActorsByType("som_trooper")
	local recalled, cooling

	Trigger.AfterDelay(10, function()
		recalled = blade.UseAbility(3)
		pod.CallDropPod(CPos.New(beacon.Location.X + 5, beacon.Location.Y), "som_trooper")
		shooter.Attack(runner, true, true)
	end)
	Trigger.AfterDelay(60, function()
		shooter.Stop()
		shooter.Stance = "HoldFire"
	end)
	-- Bolts in flight have landed by now; what the runner loses from here on is the burn.
	Trigger.AfterDelay(75, function() cooling = runner.Health end)
	Trigger.AfterDelay(300, function()
		local d = math.max(math.abs(blade.Location.X - beacon.Location.X), math.abs(blade.Location.Y - beacon.Location.Y))
		if not (recalled and d <= 2) then bad[#bad + 1] = "recall used " .. tostring(recalled) .. ", " .. d .. " cells from the beacon" end
		local came = #som.GetActorsByType("som_trooper") - troopers0
		if came ~= 6 then bad[#bad + 1] = came .. " infantrymen from the pod (expected 6)" end
		if not (cooling ~= nil and runner.Health < cooling and cooling < runner.MaxHealth) then
			bad[#bad + 1] = "runner at " .. tostring(cooling) .. " when the shooting stopped, " .. runner.Health .. " later (expected a burn)"
		end
		print("TEST som-kit " .. (#bad == 0 and "PASS" or "FAIL (" .. table.concat(bad, "; ") .. ")"))
	end)
end
