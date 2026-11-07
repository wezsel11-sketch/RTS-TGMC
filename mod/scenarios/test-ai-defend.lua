-- Scenario test: DefendBotModule (Bots.cs). Three runners attack a marine sentry turret (on HoldFire, so it does not win
-- alone; in the help case the script keeps it above half health) 34 cells from the bot's base at tick 300. It has no miner guards, and the stock squads no longer protect it, so only
-- DefendBotModule can answer.
-- DefendCase (set by a defend-case-*.lua beside this script) picks what is checked:
--   help:   by tick 1200, at least 3 riflemen are within 5 cells of the sentry and at least 2 are still within 12 cells of the
--           base: the response is sized, it does not empty the base.
--   dies:   the sentry and the runners are killed at tick 320; by tick 1500 no rifleman is left within 8 cells of where the sentry
--           stood: whoever was sent was handed back and walked home.
--   nobody: no riflemen at all; the game reaches tick 900 (the runner fails it on any engine exception).
-- Prints "TEST ai-defend-<case> PASS" or "TEST ai-defend-<case> FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	-- The attacked outpost (named miner for history; it is a sentry: miners are only ever disabled, never destroyed).
	local miner = marines.GetActorsByType("sentry-turret")[1]
	miner.Stance = "HoldFire"
	local spot = miner.Location
	local base = marines.GetActorsByType("cryo-pod")[1].Location
	local name = "ai-defend-" .. DefendCase
	local hunters = {}

	local function report(ok, why)
		if not reported then
			reported = true
			print("TEST " .. name .. " " .. (ok and "PASS" or "FAIL") .. " (" .. why .. ")")
		end
	end

	local function riflemen_near(cell, radius)
		local n, total = 0, 0
		for _, a in ipairs(marines.GetActorsByType("rifleman")) do
			if not a.IsDead then
				total = total + 1
				if math.abs(a.Location.X - cell.X) <= radius and math.abs(a.Location.Y - cell.Y) <= radius then
					n = n + 1
				end
			end
		end
		return n, total
	end

	Trigger.AfterDelay(300, function()
		hunters = Reinforcements.Reinforce(xenos, { "runner", "runner", "runner" }, { CPos.New(44, 20) }, 0)
		for _, h in ipairs(hunters) do
			h.AttackMove(spot)
		end
	end)

	if DefendCase == "dies" then
		Trigger.AfterDelay(320, function()
			miner.Kill()
			for _, h in ipairs(hunters) do
				if not h.IsDead then h.Kill() end
			end
		end)
	end

	local function poll(ticks)
		if reported then
			return
		end
		if ticks % 300 == 0 then
			local where = {}
			for _, r in ipairs(marines.GetActorsByType("rifleman")) do
				if not r.IsDead then table.insert(where, r.Location.X .. "," .. r.Location.Y .. (r.IsIdle and "i" or "")) end
			end
			for _, h in ipairs(xenos.GetActorsByType("runner")) do
				print("DBG   runner at " .. h.Location.X .. "," .. h.Location.Y .. (h.IsIdle and " idle" or "") .. " hp " .. h.Health)
			end
			print("DBG tick " .. ticks .. " outpost hp " .. (miner.IsDead and "dead" or miner.Health) .. " riflemen " .. table.concat(where, " "))
		end
		if DefendCase == "help" then
			-- Keep the sentry standing, so the defenders have something to reach (it is on HoldFire and would fall first).
			if not miner.IsDead and miner.Health < miner.MaxHealth / 2 then
				miner.Health = miner.MaxHealth
			end
			local n = riflemen_near(spot, 5)
			local home = riflemen_near(base, 12)
			if n >= 3 and home >= 2 then
				report(true, n .. " riflemen beside the miner and " .. home .. " at the base by tick " .. ticks)
			elseif ticks >= 1200 then
				report(false, n .. " riflemen beside the miner and " .. home .. " at the base at tick 1200")
			end
		elseif DefendCase == "dies" and ticks >= 1500 then
			local left = riflemen_near(spot, 8)
			report(left == 0, left .. " riflemen still where the sentry stood at tick 1500")
		elseif DefendCase == "nobody" and ticks >= 900 then
			report(true, "reached tick 900")
		end
		Trigger.AfterDelay(25, function() poll(ticks + 25) end)
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
