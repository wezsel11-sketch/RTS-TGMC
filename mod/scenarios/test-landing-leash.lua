-- Scenario test: the lobby's Landing Delay (LandingLeash on ^Unit). Ordered far out of the landing zone in the first minute, a
-- rifleman is turned back; after the delay the same order takes him there. Prints "TEST landing-leash PASS" or "... FAIL".
WorldLoaded = function()
	local rifleman = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	local home = rifleman.Location
	local far = CPos.New(home.X + 30, home.Y)
	local held = nil
	Trigger.AfterDelay(10, function() rifleman.Move(far) end)
	Trigger.AfterDelay(1000, function()
		held = rifleman.Location.X - home.X
		rifleman.Move(far)
	end)
	Trigger.AfterDelay(2400, function()
		local out = rifleman.Location.X - home.X
		-- The leash looks once a second, so a walking unit can be a cell or two past the 16-cell edge when sampled.
		local ok = held <= 19 and out >= 28
		print("TEST landing-leash " .. (ok and "PASS" or "FAIL") .. " (at 1000 ticks " .. held .. " cells out, at 2400 ticks " .. out .. ")")
	end)
end
