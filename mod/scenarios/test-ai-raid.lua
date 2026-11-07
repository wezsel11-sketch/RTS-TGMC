-- Scenario test: RaidBotModule (Bots.cs). The xeno bot has six idle runners at its silo; the marines have no bot. The map gives
-- ThreatMemory FullVision, so the xenos know the targets without scouting (map rules cannot add a camera actor). RaidCase (set by a raid-case-*.lua beside this script) picks the check:
--   pick:    a bare miner (30,6) and one with three sentries (30,34), equally far. By tick 1500 a runner has come within 4 cells of
--            the bare one and none within 6 cells of the guarded one.
--   backoff: one bare miner. When a runner comes within 8 cells, four sentries appear beside it. By tick 2000 at least one runner
--            is alive and every living runner is nearer the silo than the miner.
--   route:   a sentry wall (x 40, y 16-24) stands on the straight line from the silo to the miner (20,20), with open ground round
--            it. A runner reaches the miner (4 cells) by tick 2500, and no runner came within 3 cells of a sentry before that.
--   rich:    one bare miner worth more than the raid (map rules set its cost to 400). The target's own value is not defence: the
--            raid stays and brings the miner down to its floor (30% or less) by tick 2500.
-- Prints "TEST ai-raid-<case> PASS" or "TEST ai-raid-<case> FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local silo = xenos.GetActorsByType("resin-silo")[1].Location
	local name = "ai-raid-" .. RaidCase
	local spawned, touched = false, false

	local function report(ok, why)
		if not reported then
			reported = true
			print("TEST " .. name .. " " .. (ok and "PASS" or "FAIL") .. " (" .. why .. ")")
		end
	end

	local function dist(a, b) return math.max(math.abs(a.X - b.X), math.abs(a.Y - b.Y)) end

	local function runners()
		local alive = {}
		for _, r in ipairs(xenos.GetActorsByType("runner")) do
			if not r.IsDead then table.insert(alive, r) end
		end
		return alive
	end

	local function nearest(cell)
		local best = 999
		for _, r in ipairs(runners()) do
			best = math.min(best, dist(r.Location, cell))
		end
		return best
	end

	local function poll(ticks)
		if reported then
			return
		end
		if ticks % 250 == 0 then
			local where = {}
			for _, r in ipairs(runners()) do table.insert(where, r.Location.X .. "," .. r.Location.Y .. (r.IsIdle and "i" or "")) end
			print("DBG tick " .. ticks .. " runners " .. table.concat(where, " "))
		end
		if RaidCase == "pick" then
			local bare, guarded = CPos.New(30, 6), CPos.New(30, 34)
			if nearest(guarded) <= 6 then
				report(false, "a runner went for the guarded miner by tick " .. ticks)
			elseif nearest(bare) <= 4 then
				report(true, "raided the bare miner by tick " .. ticks)
			elseif ticks >= 1500 then
				report(false, "no runner reached the bare miner by tick 1500")
			end
		elseif RaidCase == "backoff" then
			local miner = CPos.New(30, 6)
			if not spawned and nearest(miner) <= 8 then
				spawned = true
				for _, x in ipairs({ 28, 29, 31, 32 }) do
					Actor.Create("sentry-turret", true, { Owner = marines, Location = CPos.New(x, 8) })
				end
			end
			if ticks >= 2000 then
				local alive, home = runners(), true
				for _, r in ipairs(alive) do
					if dist(r.Location, silo) >= dist(r.Location, miner) then home = false end
				end
				report(spawned and #alive > 0 and home, "sentries spawned " .. tostring(spawned) .. ", " .. #alive .. " runners alive, all nearer the silo " .. tostring(home))
			end
		elseif RaidCase == "rich" then
			local m = marines.GetActorsByType("miner")[1]
			if m.Health * 100 <= m.MaxHealth * 30 then
				report(true, "miner brought down by tick " .. ticks)
			elseif ticks >= 2500 then
				report(false, "miner at " .. m.Health .. " of " .. m.MaxHealth .. " at tick 2500")
			end
		elseif RaidCase == "route" then
			for _, t in ipairs(marines.GetActorsByType("sentry-turret")) do
				if not t.IsDead and nearest(t.Location) <= 3 then touched = true end
			end
			if nearest(CPos.New(20, 20)) <= 4 then
				report(not touched, "reached the miner by tick " .. ticks .. ", came within 3 cells of a sentry first " .. tostring(touched))
			elseif ticks >= 2500 then
				report(false, "no runner reached the miner by tick 2500")
			end
		end
		Trigger.AfterDelay(25, function() poll(ticks + 25) end)
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
