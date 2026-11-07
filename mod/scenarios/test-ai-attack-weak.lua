-- Scenario test: AttackTargetBotModule (Bots.cs). The marine bot (hard) gets eight riflemen, which form its attack squad. The map
-- gives ThreatMemory FullVision, so the bot knows every xeno structure. Xeno targets, all turrets on HoldFire:
--   A (44,6): a mini-silo and one turret, within the squad's reach but defended;
--   B (44,34): a bare mini-silo, as far as A;
--   C (28,4): a mini-silo behind two turrets, much nearer, but more than the squad can beat (beyond the stock squad's
--     12-cell scan from the base, which would engage anything that close whatever its target);
--   the main silo (60,20) behind three turrets.
-- PASS if B is the first mini-silo destroyed, by tick 3000, while A is still undamaged (riflemen shoot from 9 cells, so passing
-- shots may scratch C: it is the target choice that is checked, not the walk).
-- Prints "TEST ai-attack-weak PASS" or "TEST ai-attack-weak FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	for _, t in ipairs(xenos.GetActorsByType("resin-turret")) do
		t.Stance = "HoldFire"
	end
	local A, B, C, silo = CPos.New(44, 6), CPos.New(44, 34), CPos.New(28, 4), CPos.New(60, 20)

	local function report(ok, why)
		if not reported then
			reported = true
			print("TEST ai-attack-weak " .. (ok and "PASS" or "FAIL") .. " (" .. why .. ")")
		end
	end

	local function dist(a, b) return math.max(math.abs(a.X - b.X), math.abs(a.Y - b.Y)) end

	-- The squad's mean cell, for the debug trace.
	local function centre()
		local x, y, n = 0, 0, 0
		for _, r in ipairs(marines.GetActorsByType("rifleman")) do
			if not r.IsDead then x, y, n = x + r.Location.X, y + r.Location.Y, n + 1 end
		end
		if n == 0 then return nil end
		return CPos.New(math.floor(x / n), math.floor(y / n))
	end

	local function poll(ticks)
		if reported then
			return
		end
		local c = centre()
		local silos = {}
		for _, m in ipairs(xenos.GetActorsByType("mini-silo")) do
			if not m.IsDead then silos[m.Location.X .. "," .. m.Location.Y] = m end
		end
		if ticks % 250 == 0 and c then
			local hp = {}
			for k, m in pairs(silos) do table.insert(hp, k .. "=" .. m.Health) end
			print("DBG tick " .. ticks .. " squad centre " .. c.X .. "," .. c.Y .. " silos " .. table.concat(hp, " "))
		end
		local a, b, cc = silos["44,6"], silos["44,34"], silos["28,4"]
		if a == nil or cc == nil then
			report(false, (a == nil and "A" or "C") .. " was destroyed first, by tick " .. ticks)
		elseif b == nil then
			report(a.Health == a.MaxHealth, "B destroyed first by tick " .. ticks .. ", A at " .. a.Health .. " of " .. a.MaxHealth)
		elseif ticks >= 3000 then
			report(false, "no mini-silo destroyed by tick 3000")
		end
		Trigger.AfterDelay(25, function() poll(ticks + 25) end)
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
