-- Scenario test (see mod/test_scenarios.sh): the xeno and marine abilities, started from script. The orders a player gives
-- (the deploy key, a support power) have no Lua hook, so this starts each ability through its external condition and checks
-- its effect against an identical unit that did not get it:
--   pounce:  a pouncing Runner stuns the marine it hits, who then cannot walk away; a normal Runner's marine can
--   stealth: a stealthed Hunter is not shot at while it closes in, an ordinary one is
--   screech: a screeched marine walks much slower than a normal one
--   flare:   the flare actor the power drops can be created
-- Prints "TEST abilities PASS" or "TEST abilities FAIL" with what each part saw.
local results = {}

local function report()
	local ok, text = true, {}
	for _, name in ipairs({ "pounce", "stealth", "screech", "flare" }) do
		local r = results[name]
		if not r then
			ok = false
			table.insert(text, name .. ": no result")
		else
			ok = ok and r.ok
			table.insert(text, name .. (r.ok and " ok" or " FAILED") .. " (" .. r.note .. ")")
		end
	end
	print("TEST abilities " .. (ok and "PASS" or "FAIL") .. " - " .. table.concat(text, "; "))
end

local function finished()
	return results.pounce and results.stealth and results.screech and results.flare
end

WorldLoaded = function()
	local marines, xenos = Player.GetPlayer("Marines"), Player.GetPlayer("Xenos")
	local function at(player, type, x, y)
		for _, a in ipairs(player.GetActorsByType(type)) do
			if a.Location.X == x and a.Location.Y == y then
				return a
			end
		end
	end

	-- pounce
	local r1, m1 = at(xenos, "runner", 3, 3), at(marines, "rifleman", 8, 3)
	local control = at(marines, "rifleman", 30, 14) -- nobody attacks this one: it shows how far a marine walks in the same time
	r1.GrantCondition("pouncing", 400)
	local stunnedAt, stunnedFrom
	local function pounce(tick)
		if results.pounce then
			return
		end
		if not stunnedAt and not m1.IsDead and m1.Health < m1.MaxHealth - 30 then
			stunnedAt, stunnedFrom = tick, m1.Location.X
			r1.Kill() -- the Runner has done its part; this keeps the stunned marine alive for the check
			m1.Move(CPos.New(8, 0))
			control.Move(CPos.New(30, 11))
		end
		if stunnedAt and m1.IsDead then
			results.pounce = { ok = false, note = "the stunned marine died before the check" }
			return
		end
		if stunnedAt and tick >= stunnedAt + 40 then
			local movedStunned = math.abs(m1.Location.Y - 3)
			local movedControl = math.abs(control.Location.Y - 14)
			results.pounce = { ok = movedStunned == 0 and movedControl >= 1, note = "hit at tick " .. stunnedAt .. ", the stunned marine moved " .. movedStunned .. " cells, the control " .. movedControl .. " (control now at " .. control.Location.X .. "," .. control.Location.Y .. ", stunned marine at " .. m1.Location.X .. "," .. m1.Location.Y .. ")" }
			return
		end
		if tick >= 300 then
			results.pounce = { ok = false, note = "the pounce never hit a marine hard (rifleman health " .. m1.Health .. ")" }
			return
		end
		Trigger.AfterDelay(5, function() pounce(tick + 5) end)
	end
	Trigger.AfterDelay(5, function() pounce(5) end)

	-- stealth
	local h1, h2 = at(xenos, "hunter", 16, 3), at(xenos, "hunter", 16, 9)
	h1.GrantCondition("stealth", 400)
	Trigger.AfterDelay(70, function()
		results.stealth = { ok = h1.Health == h1.MaxHealth and h2.Health < h2.MaxHealth,
			note = "stealthed hunter health " .. h1.Health .. " of " .. h1.MaxHealth .. ", ordinary hunter " .. h2.Health }
	end)

	-- screech
	local m5, m6 = at(marines, "rifleman", 3, 17), at(marines, "rifleman", 3, 20)
	m5.GrantCondition("screeched", 400)
	m5.Move(CPos.New(30, 17))
	m6.Move(CPos.New(30, 20))
	Trigger.AfterDelay(100, function()
		local slow, normal = m5.Location.X - 3, m6.Location.X - 3
		results.screech = { ok = normal >= 3 and slow * 10 <= normal * 7, note = "screeched marine walked " .. slow .. " cells, the other " .. normal }
	end)

	-- flare
	local flare = Actor.Create("flare", true, { Owner = marines, Location = CPos.New(20, 24) })
	Trigger.AfterDelay(10, function()
		results.flare = { ok = flare ~= nil and flare.IsInWorld, note = "flare actor " .. (flare ~= nil and "created" or "missing") }
	end)

	local function wait(tick)
		if finished() then
			report()
		elseif tick >= 400 then
			report()
		else
			Trigger.AfterDelay(10, function() wait(tick + 10) end)
		end
	end
	Trigger.AfterDelay(10, function() wait(10) end)
end
