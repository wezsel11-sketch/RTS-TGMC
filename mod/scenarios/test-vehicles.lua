-- Scenario test: the vehicles from TGMC (units.yaml). The tank and the SOM tank each shoot a tough xeno target; a rifleman boards
-- the APC and gets off again. By tick 400 both targets were hurt, the APC had its passenger aboard, and he is back on foot.
-- Prints "TEST vehicles PASS" or "TEST vehicles FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local targets = xenos.GetActorsByType("crusher")
	table.sort(targets, function(a, b) return a.Location.Y < b.Location.Y end)
	local hp = { targets[1].Health, targets[2].Health }
	local tank = marines.GetActorsByType("tank")[1]
	local somtank = marines.GetActorsByType("som-tank")[1]
	local apc = marines.GetActorsByType("apc")[1]
	local rifle = marines.GetActorsByType("rifleman")[1]
	local boarded = false
	for _, t in ipairs(targets) do t.Stance = "HoldFire" end
	-- Lua orders queue behind what a unit is doing: a rifleman shooting at a crusher would never get round to boarding.
	rifle.Stance = "HoldFire"
	Trigger.AfterDelay(10, function()
		tank.Attack(targets[1], true, true)
		somtank.Attack(targets[2], true, true)
		rifle.EnterTransport(apc)
	end)
	local function poll(ticks)
		if apc.PassengerCount > 0 then
			boarded = true
			apc.UnloadPassengers()
		end
		if ticks >= 400 then
			local onFoot = not rifle.IsDead and rifle.IsInWorld
			local ok = targets[1].Health < hp[1] and targets[2].Health < hp[2] and boarded and onFoot
			print("TEST vehicles " .. (ok and "PASS" or "FAIL") .. " (tank target lost " .. (hp[1] - targets[1].Health) ..
				", SOM tank target lost " .. (hp[2] - targets[2].Health) .. ", boarded " .. tostring(boarded) .. ", back on foot " .. tostring(onFoot) .. ")")
			return
		end
		Trigger.AfterDelay(10, function() poll(ticks + 10) end)
	end
	poll(0)
end
