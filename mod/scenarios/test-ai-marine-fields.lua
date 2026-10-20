-- Scenario test: marine AI and xeno AI both play on a map with three ore fields. The fields start dormant: a marine engineer
-- claims one by repairing it (it becomes a marine miner on the same cell), and the xenos then go for that miner and disable it
-- (never destroy). For each field it records when marines claimed it, when xenos disabled it, and how many marine combat units
-- stood within 8 cells when the first attack came. Prints one line per field, then "TEST ai-marine-fields PASS|FAIL" (marines
-- claimed a field and xenos disabled one) and "TEST ai-marine-defense PASS|FAIL" (a miner under attack had marine defenders near it).
local reported = false
local xeno_units = {"runner", "hunter", "sentinel", "warrior", "spitter", "drone", "praetorian", "defiler", "boiler", "carrier", "queen"}
local defenders = {"rifleman", "smartgunner", "machinegunner", "grenadier", "flamer"}

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local neutral = Player.GetPlayer("Neutral")
	local records = {}
	for i, f in ipairs(neutral.GetActorsByType("miner-field")) do
		records[i] = {x = f.Location.X, y = f.Location.Y}
	end

	local function near_defenders(x, y)
		local n = 0
		for _, type in ipairs(defenders) do
			for _, a in ipairs(marines.GetActorsByType(type)) do
				if not a.IsDead and math.abs(a.Location.X - x) <= 8 and math.abs(a.Location.Y - y) <= 8 then
					n = n + 1
				end
			end
		end
		return n
	end

	local xenos = Player.GetPlayer("Xenos")
	local function near_xenos(x, y)
		local n = 0
		for _, type in ipairs(xeno_units) do
			for _, a in ipairs(xenos.GetActorsByType(type)) do
				if not a.IsDead and math.abs(a.Location.X - x) <= 8 and math.abs(a.Location.Y - y) <= 8 then
					n = n + 1
				end
			end
		end
		return n
	end

	-- The marine miner standing on the field's cell, if any.
	local function miner_at(r)
		for _, m in ipairs(marines.GetActorsByType("miner")) do
			if not m.IsDead and m.Location.X == r.x and m.Location.Y == r.y then
				return m
			end
		end
		return nil
	end

	local function finish(ticks)
		reported = true
		local claimed, disabled, attacked_with_defence, attacked = 0, 0, false, false
		for i, r in ipairs(records) do
			print("DBG field " .. i .. " at " .. r.x .. "," .. r.y .. ": claimed " .. tostring(r.claimed or "never") ..
				", attacked " .. tostring(r.attacked or "never") .. ", disabled " .. tostring(r.disabled or "never") ..
				", marine defenders when attacked " .. tostring(r.defenders or "-"))
			if r.claimed then claimed = claimed + 1 end
			if r.disabled then disabled = disabled + 1 end
			if r.attacked then attacked = true end
			if r.defenders and r.defenders > 0 then attacked_with_defence = true end
		end
		local guards, losses = 0, 0
		for _, r in ipairs(records) do
			losses = losses + (r.losses or 0)
			if r.claimed then
				for _, d in ipairs(marines.GetActorsByType("sentry-turret")) do
					if not d.IsDead and math.abs(d.Location.X - r.x) <= 8 and math.abs(d.Location.Y - r.y) <= 8 then
						guards = guards + 1
					end
				end
			end
		end
		print("DBG sentry turrets within 8 cells of claimed fields: " .. guards .. ", sentries and cades built in total: " .. (#marines.GetActorsByType("sentry-turret") + #marines.GetActorsByType("cade")))
		print("TEST ai-marine-fields " .. ((claimed >= 1 and disabled >= 1) and "PASS" or "FAIL") .. " (claimed " .. claimed .. ", disabled " .. disabled .. " by tick " .. ticks .. ")")
		print("TEST ai-marine-defense " .. ((attacked_with_defence and losses > 0) and "PASS" or "FAIL") .. " (" .. (attacked and "attacked miners" or "no miner attacked") .. ", defenders near an attacked miner: " .. tostring(attacked_with_defence) .. ", xeno units lost near attacked miners: " .. losses .. ")")
	end

	local function poll(ticks)
		if reported then
			return
		end
		for _, r in ipairs(records) do
			local m = miner_at(r)
			if m then
				if not r.claimed then
					r.claimed = ticks
					r.hp = m.Health
				end
				if not r.attacked and m.Health < r.hp then
					r.attacked = ticks
					r.defenders = near_defenders(r.x, r.y)
					r.xenosBefore = near_xenos(r.x, r.y)
					r.attackTick = ticks
				end
				-- Disabled: the xenos have brought the miner down to its floor (25% of 250, with a few points of slack).
				if not r.disabled and m.Health * 100 <= m.MaxHealth * 30 then
					r.disabled = ticks
				end
				r.hp = m.Health
			end
		end
		for _, r in ipairs(records) do
			if r.attackTick and not r.losses and ticks - r.attackTick >= 300 then
				r.losses = math.max(0, r.xenosBefore - near_xenos(r.x, r.y))
			end
		end
		-- Run the full 6000 ticks: sentries go up after a claim, and the xenos go for a miner once it is up.
		if ticks >= 6000 then
			finish(ticks)
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end

	-- Status every 1000 ticks: marine cash, engineers (idle or not), miners and sentries, to see why defences lag.
	local function status(ticks)
		if reported then
			return
		end
		local eng, idle = marines.GetActorsByType("engineer"), 0
		for _, e in ipairs(eng) do
			if not e.IsDead and e.IsIdle then idle = idle + 1 end
		end
		print("DBG status tick " .. ticks .. ": cash " .. marines.Cash .. ", engineers " .. #eng .. " (idle " .. idle .. "), miners " ..
			#marines.GetActorsByType("miner") .. ", sentries " .. #marines.GetActorsByType("sentry-turret") ..
			", cades " .. #marines.GetActorsByType("cade"))
		Trigger.AfterDelay(1000, function() status(ticks + 1000) end)
	end
	Trigger.AfterDelay(1000, function() status(1000) end)
	Trigger.AfterDelay(25, function() poll(25) end)
end
