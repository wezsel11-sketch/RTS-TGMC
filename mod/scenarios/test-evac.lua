-- Scenario test: the Evac mission (mission-evac.lua), one case per map, picked by an evac-case-*.lua beside this script (EvacCase).
-- Timings are cut down through ConfigOverride.
--   target: a bare miner in the north, one with three sentries in the south, and the cryo pod with three sentries. The first wave goes for the bare one, from the
--           edge cell nearest it (32,2).
--   payout: two waves; when the second comes, the marines' cash has grown by the first wave's pay (the vendors' trickle aside).
--   board:  the Alamo flies in (it is not down the moment it appears) and lands; a rifleman walks onto it. When it leaves on its own,
--           the objective is complete with one aboard.
--   empty:  the Alamo lands and leaves with no one aboard: the objective fails.
--   early:  a rifleman boards, then the ship is launched (as Deploy does) long before its time: the objective is complete at once.
--   full:   the real timings and the full base, nobody playing; the map makes the cryo pod and vendors all but unbreakable, so
--           the match runs its course. Every wave comes, the Alamo lands and leaves (empty: the objective fails), and nothing in
--           the script broke on the way.
-- Prints "TEST evac-<case> PASS" or "TEST evac-<case> FAIL".
local reported = false

local function report(ok, why)
	if not reported then
		reported = true
		print("TEST evac-" .. EvacCase .. " " .. (ok and "PASS" or "FAIL") .. " (" .. why .. ")")
	end
end

ConfigOverride = function(config)
	if EvacCase == "full" then return end
	config.assaultInterval = 100000
	if EvacCase == "target" then
		config.waves = { { delay = 50, pay = 100, units = { { "runner", 2 } } } }
		config.landDelay = 100000
	elseif EvacCase == "payout" then
		config.waves = { { delay = 50, pay = 400, units = {} }, { delay = 100, pay = 100, units = {} } }
		config.landDelay = 100000
	else
		config.waves = { { delay = 20, pay = 0, units = {} } }
		config.landDelay = 30
		config.shuttleWait = EvacCase == "early" and 5000 or 400
	end
end

AfterStart = function()
	local marines = Player.GetPlayer("Marines")
	if EvacCase == "full" then
		-- A lost match pauses the world, so the end is caught by polling, not by one late timer.
		local function poll(ticks)
			if ticks % 1000 == 0 then print("DBG tick " .. ticks .. ": " .. WavesSent .. " waves, xenos " .. #Player.GetPlayer("Xenos").GetActors()) end
			if Finished then
				report(WavesSent == #Config.waves and Shuttle ~= nil, WavesSent .. " waves sent, Alamo down " .. tostring(Shuttle ~= nil) .. ", ended at tick " .. ticks)
			elseif ticks >= 16000 then
				report(false, WavesSent .. " waves by tick 16000, Alamo down " .. tostring(Shuttle ~= nil) .. ", not ended")
			else
				Trigger.AfterDelay(50, function() poll(ticks + 50) end)
			end
		end
		poll(0)
	elseif EvacCase == "target" then
		Trigger.AfterDelay(60, function()
			local t, s = LastWaveTarget, LastWaveSpawn
			local ok = t ~= nil and t.Location.Y == 8 and s ~= nil and s.X == 32 and s.Y == 2
			report(ok, "target " .. (t and (t.Type .. " at " .. t.Location.X .. "," .. t.Location.Y) or "none") ..
				", spawn " .. (s and (s.X .. "," .. s.Y) or "none"))
		end)
	elseif EvacCase == "payout" then
		local before
		Trigger.AfterDelay(55, function() before = marines.Cash end)
		Trigger.AfterDelay(155, function()
			local gained = marines.Cash - before
			report(gained >= 400 and gained < 450, "cash grew by " .. gained .. " when wave 2 came")
		end)
	else
		-- Lands at tick 50. The rifleman steps on at once; for "empty" it stays put.
		local rifle = marines.GetActorsByType("rifleman")[1]
		if EvacCase ~= "empty" then
			Trigger.AfterDelay(60, function() rifle.Move(CPos.New(44, 24)) end)
		end
		if EvacCase == "early" then
			Trigger.AfterDelay(250, function()
				if Shuttle ~= nil and Shuttle.IsInWorld then Shuttle.GrantCondition("launch") end
			end)
		end
		-- The ship appears at tick 50 and takes a while to come down, and as long again to climb away once launched.
		local airborne
		Trigger.AfterDelay(52, function() airborne = Shuttle ~= nil and not Shuttle.Landed end)
		-- A won match pauses the world soon after, so the end is caught by polling, as in "full".
		local deadline = EvacCase == "early" and 400 or 700
		local function poll(ticks)
			local done = marines.IsObjectiveCompleted(Objective)
			local failed = marines.IsObjectiveFailed(Objective)
			if done or failed or ticks >= deadline then
				local ok = airborne and ((EvacCase == "empty") and failed or (done and Aboard == 1))
				report(ok, "flew in " .. tostring(airborne) .. ", aboard " .. Aboard .. ", completed " .. tostring(done) .. ", failed " .. tostring(failed) .. " by tick " .. ticks)
			else
				Trigger.AfterDelay(5, function() poll(ticks + 5) end)
			end
		end
		poll(0)
	end
end
