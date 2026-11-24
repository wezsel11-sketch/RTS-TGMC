-- Scenario test: the second-wave upgrades. Every one can be created and hands out its prerequisite; and two of them are measured:
-- Thick Weeds (a hurt runner on weeds mends 1 more per second) and Sticky Weeds (a marine crosses a strip of weeds slower).
-- Prints "TEST upgrades2 PASS" or "TEST upgrades2 FAIL (what failed)".
MarineUps = { "upgrade-attach-barrel", "upgrade-attach-bayonet", "upgrade-attach-harness", "upgrade-attach-scope", "upgrade-plasteel-cades", "upgrade-sentry" }
XenoUps = { "upgrade-thick-weeds", "upgrade-sticky-weeds", "upgrade-fast-weeds", "upgrade-hardened-resin", "upgrade-turret-reach" }

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local marines = Player.GetPlayer("Marines")
	local bad = {}
	local runner = xenos.GetActorsByType("runner")[1]
	runner.Stance = "HoldFire"
	local rifles = marines.GetActorsByType("rifleman")
	table.sort(rifles, function(a, b) return a.Location.Y < b.Location.Y end)
	for _, r in ipairs(rifles) do r.Stance = "HoldFire" end

	-- Walks a marine 12 cells east and calls back with the ticks it took.
	local walk = function(unit, done)
		local goal = CPos.New(unit.Location.X + 12, unit.Location.Y)
		local started = DateTime.GameTime
		unit.Move(goal)
		local function poll()
			if unit.Location == goal then done(DateTime.GameTime - started) else Trigger.AfterDelay(2, poll) end
		end
		poll()
	end

	local plain, sticky, mend0, mend1, from
	walk(rifles[1], function(t) plain = t end)
	runner.Health = 20
	-- The runner mends once five seconds have passed without a hit.
	Trigger.AfterDelay(200, function() from = runner.Health end)
	Trigger.AfterDelay(450, function()
		mend0 = runner.Health - from
		for _, u in ipairs(MarineUps) do Actor.Create(u, true, { Owner = marines }) end
		for _, u in ipairs(XenoUps) do Actor.Create(u, true, { Owner = xenos }) end
	end)
	Trigger.AfterDelay(500, function()
		for _, u in ipairs(MarineUps) do if not marines.HasPrerequisites({ u }) then bad[#bad + 1] = u .. " gives no prerequisite" end end
		for _, u in ipairs(XenoUps) do if not xenos.HasPrerequisites({ u }) then bad[#bad + 1] = u .. " gives no prerequisite" end end
		runner.Health = 20
		walk(rifles[2], function(t) sticky = t end)
	end)
	Trigger.AfterDelay(700, function() from = runner.Health end)
	Trigger.AfterDelay(950, function()
		mend1 = runner.Health - from
		-- On weeds and resting it mends 5 a second; Thick Weeds adds 1, which is 10 more over the 250 ticks.
		if not (mend0 >= 40 and mend1 - mend0 >= 8 and mend1 - mend0 <= 12) then bad[#bad + 1] = "mending " .. mend0 .. " then " .. mend1 .. " in 250 ticks (expected 10 more)" end
		if plain == nil or sticky == nil or sticky * 100 < plain * 110 then bad[#bad + 1] = "crossing took " .. tostring(plain) .. " then " .. tostring(sticky) .. " ticks (expected a tenth slower or more)" end
		print("TEST upgrades2 " .. (#bad == 0 and "PASS" or "FAIL (" .. table.concat(bad, "; ") .. ")"))
	end)
end
