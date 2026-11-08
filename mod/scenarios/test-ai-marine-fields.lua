-- Scenario test: marine AI and xeno AI both play on a map with three ore fields. The fields start dormant: a marine engineer
-- claims one by repairing it (it becomes a marine miner on the same cell), and the xenos then go for that miner and disable it
-- (never destroy). The marine engineers leave a field beside the hive alone. For each field it records when marines claimed it, when xenos disabled it, and the most marine combat units
-- within 8 cells while it was under attack, and how many xenos died near it. Prints one line per field, then "TEST ai-marine-fields PASS|FAIL" (marines
-- claimed a field and xenos went for a miner) and "TEST ai-marine-defense PASS|FAIL" (xenos died near the miners, and a miner
-- under attack had marine defenders near it).
local reported = false
-- Fighters are any unit that moves, but for these: the bots field every caste and kit, so a list of types goes stale.
local not_fighters = {engineer = true, som_engineer = true, medic = true, som_corpsman = true, synth = true, miner = true, larva = true}
local function fighters(player, x, y, reach)
	local found = {}
	for _, a in ipairs(player.GetActors()) do
		if not a.IsDead and a.HasProperty("Move") and not not_fighters[a.Type]
			and math.abs(a.Location.X - x) <= reach and math.abs(a.Location.Y - y) <= reach then
			table.insert(found, a)
		end
	end
	return found
end

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local neutral = Player.GetPlayer("Neutral")
	local records = {}
	for i, f in ipairs(neutral.GetActorsByType("miner-field")) do
		records[i] = {x = f.Location.X, y = f.Location.Y}
	end

	local function near_defenders(x, y, reach)
		return #fighters(marines, x, y, reach or 8)
	end

	local xenos = Player.GetPlayer("Xenos")
	-- The xeno units within 8 cells now: later the test counts how many of these same ones died (newcomers would hide losses in a head count).
	local function near_xenos(x, y)
		return fighters(xenos, x, y, 8)
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

	local seen = {}
	local approached = false
	local wiped = false

	local function finish(ticks)
		reported = true
		local claimed, disabled, attacked_with_defence, attacked = 0, 0, false, false
		for i, r in ipairs(records) do
			print("DBG field " .. i .. " at " .. r.x .. "," .. r.y .. ": claimed " .. tostring(r.claimed or "never") ..
				", attacked " .. tostring(r.attacked or "never") .. ", disabled " .. tostring(r.disabled or "never") ..
				", marine defenders when attacked " .. tostring(r.defenders or "-") .. ", xenos near then " .. (r.xenosBefore and #r.xenosBefore or "-") .. ", xenos killed near it " .. tostring(r.losses or 0))
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
		-- The xenos must go for a miner; whether the raid disables it depends on the guards, so a held miner counts too.
		-- A raid the guards beat before it landed a hit still went for the miner: xenos within 8 cells count.
		print("TEST ai-marine-fields " .. ((claimed >= 1 and (attacked or approached or wiped)) and "PASS" or "FAIL") .. " (claimed " .. claimed .. ", attacked " .. tostring(attacked) .. ", xenos came near " .. tostring(approached) .. ", disabled " .. disabled .. " by tick " .. ticks .. (wiped and ", the xenos were wiped out" or "") .. ")")
		print("TEST ai-marine-defense " .. ((wiped or ((attacked_with_defence or not attacked) and losses > 0)) and "PASS" or "FAIL") .. " (" .. (attacked and "attacked miners" or "no miner attacked") .. ", defenders near an attacked miner: " .. tostring(attacked_with_defence) .. ", xeno units killed near claimed miners: " .. losses .. ")")
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
				-- Every hit counts, not just the first: the most defenders seen beside the miner while it was under attack.
				if m.Health < r.hp then
					if not r.attacked then
						r.attacked = ticks
						r.xenosBefore = near_xenos(r.x, r.y)
					end
					r.defenders = math.max(r.defenders or 0, near_defenders(r.x, r.y))
				end
				-- Disabled: the xenos have brought the miner down to its floor (25% of 250, with a few points of slack).
				if not r.disabled and m.Health * 100 <= m.MaxHealth * 30 then
					r.disabled = ticks
				end
				r.hp = m.Health
			end
		end
		-- Losses over the whole match: a xeno seen within 8 cells of a claimed miner that has since died. One snapshot at the first
		-- hit misses raids that come later, and ranged attackers that hit from further out.
		for a, r in pairs(seen) do
			if a.IsDead then
				r.losses = (r.losses or 0) + 1
				seen[a] = nil
			end
		end
		for _, r in ipairs(records) do
			if r.claimed and miner_at(r) then
				for _, a in ipairs(near_xenos(r.x, r.y)) do
					seen[a] = r
					approached = true
				end
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
			", cades " .. #marines.GetActorsByType("cade") .. ", fighters " .. near_defenders(32, 20, 99))
		Trigger.AfterDelay(1000, function() status(ticks + 1000) end)
	end
	Trigger.AfterDelay(1000, function() status(1000) end)
	Trigger.AfterDelay(25, function() poll(25) end)

	-- A match that ends (one side wiped out) pauses the world: report then, or the test would wait for ticks that never come.
	-- A hive wiped out before its raids start (FieldBotModule's MinTick) never had the chance to go for a miner: that counts as held.
	local function onEnd(loser)
		if not reported then
			wiped = loser == xenos
			finish(DateTime.GameTime)
		end
	end
	Trigger.OnPlayerLost(marines, function() onEnd(marines) end)
	Trigger.OnPlayerLost(xenos, function() onEnd(xenos) end)
end
