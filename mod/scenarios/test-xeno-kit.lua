-- Scenario test: three of the xeno abilities taken from TGMC's action lists.
-- Portal: a wraith opens a pair, steps off its end, and a runner sent onto that end comes out at the far one.
-- Rewind: a marine rewound by a second wraith walks away and is put back where it stood.
-- Drain: a hurt gorger drinks from the marine beside it: the gorger mends, the marine is hurt.
-- Prints one "TEST xeno-kit PASS" or "FAIL" line with the three results.
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local marines = Player.GetPlayer("Marines")
	for _, a in ipairs(xenos.GetActors()) do if a.HasProperty("Stance") then a.Stance = "HoldFire" end end
	for _, a in ipairs(marines.GetActors()) do if a.HasProperty("Stance") then a.Stance = "HoldFire" end end
	local wraiths = xenos.GetActorsByType("wraith")
	table.sort(wraiths, function(a, b) return a.Location.Y < b.Location.Y end)
	local opener, rewinder = wraiths[1], wraiths[2]
	local runner = xenos.GetActorsByType("runner")[1]
	local gorger = xenos.GetActorsByType("gorger")[1]
	local rifles = marines.GetActorsByType("rifleman")
	table.sort(rifles, function(a, b) return a.Location.Y < b.Location.Y end)
	local walker, victim = rifles[1], rifles[2]
	local near, far = opener.Location, CPos.New(18, 6)
	local stood = walker.Location
	gorger.Health = math.floor(gorger.MaxHealth / 2)
	local gorger0, victim0 = gorger.Health, victim.Health
	local opened, rewound, drained
	Trigger.AfterDelay(20, function()
		opened = opener.UseAbilityAt(2, far)
		rewound = rewinder.UseAbilityOn(3, walker)
		drained = gorger.UseAbility(2)
		walker.Move(CPos.New(stood.X + 6, stood.Y))
	end)
	Trigger.AfterDelay(30, function()
		opener.Move(CPos.New(near.X, near.Y - 3))
	end)
	Trigger.AfterDelay(80, function()
		runner.Move(near)
	end)
	local awayAt
	Trigger.AfterDelay(130, function() awayAt = walker.Location end)
	Trigger.AfterDelay(260, function()
		local ends = #xenos.GetActorsByType("wraith-portal")
		local d = math.max(math.abs(runner.Location.X - far.X), math.abs(runner.Location.Y - far.Y))
		-- Its body must stand where its cell is: a teleport in mid-step used to leave it drawn back toward the entry.
		local c, at = Map.CenterOfCell(runner.Location), runner.CenterPosition
		local off = math.max(math.abs(c.X - at.X), math.abs(c.Y - at.Y))
		local portal = opened and ends == 2 and d <= 2 and off < 256
		local back = math.max(math.abs(walker.Location.X - stood.X), math.abs(walker.Location.Y - stood.Y))
		local rewind = rewound and awayAt ~= stood and back <= 1
		local drain = drained and gorger.Health > gorger0 and victim.Health < victim0
		print("TEST xeno-kit " .. ((portal and rewind and drain) and "PASS" or "FAIL") ..
			" (portal " .. tostring(portal) .. ": used " .. tostring(opened) .. ", ends " .. ends .. ", runner " .. d .. " cells from the far end, " .. off .. " off its cell; rewind " ..
			tostring(rewind) .. ": used " .. tostring(rewound) .. ", walked to " .. tostring(awayAt) .. ", now " .. back .. " cells from the start; drain " ..
			tostring(drain) .. ": used " .. tostring(drained) .. ", gorger " .. gorger0 .. " to " .. gorger.Health .. ", marine " .. victim0 .. " to " .. victim.Health .. ")")
	end)
end
