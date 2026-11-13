-- Scenario test: a hurt xeno mends on weeds and gains plasma faster there; one on bare ground does neither.
-- Prints "TEST weed-heal PASS" or "TEST weed-heal FAIL".
WorldLoaded = function()
	Player.GetPlayer("Marines").GetActorsByType("rifleman")[1].Stance = "HoldFire"
	local runners = Player.GetPlayer("Xenos").GetActorsByType("runner")
	local on, off = runners[1], runners[2]
	if on.Location.X > off.Location.X then on, off = off, on end
	on.Health = 40
	off.Health = 40
	local plasmaOn, plasmaOff = on.Plasma, off.Plasma
	Trigger.AfterDelay(300, function()
		local ok = on.Health >= 65 and off.Health == 40 and on.Plasma - plasmaOn > off.Plasma - plasmaOff
		print("TEST weed-heal " .. (ok and "PASS" or "FAIL") .. " (on weeds " .. on.Health .. " health, +" .. (on.Plasma - plasmaOn)
			.. " plasma; off weeds " .. off.Health .. " health, +" .. (off.Plasma - plasmaOff) .. " plasma)")
	end)
end
