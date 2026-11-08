-- Scenario test: the abilities added so the castes' kits follow TGMC's (crest toss, ravager charge and ravage, defender charge,
-- psychic shield and crush, fire storm, inferno, fire charge, spiderling, trap, flay, pincushion). Each caste stands beside a
-- tough marine; both hold fire, so only the abilities hurt. Abilities go at ticks 20, 90 and 160; by tick 230:
--   every call returned true;  each caste's marine was hurt (the widow's and carrier's excepted);  a spiderling stands;
--   a hugger trap stands;  the warlock's shield was up right after it was raised;  Flay (after Pincushion spent some) gave the
--   puppeteer plasma, its biomass;  Fire Charge into the marine standing in Inferno's flames put them out and gave plasma back. Then the carrier's marine walks up to the trap;
--   by tick 520 a facehugger has jumped out of it.
-- Prints "TEST caste-kits PASS" or "TEST caste-kits FAIL" with what failed.
local castes = { "crusher", "ravager", "defender", "warlock", "pyrogen", "widow", "carrier", "puppeteer" }
local hurtCastes = { "crusher", "ravager", "defender", "warlock", "pyrogen", "puppeteer" }

-- What each caste does at each moment: { tick, slot, how } with how "self" (UseAbility), "marine" (UseAbilityAt the marine's
-- cell) or "cell" (UseAbilityAt two cells behind the caste).
local plan = {
	crusher = { { 20, 2, "self" } },
	ravager = { { 20, 4, "self" }, { 90, 3, "self" } },
	defender = { { 20, 3, "self" } },
	warlock = { { 20, 3, "marine" }, { 90, 2, "self" } },
	pyrogen = { { 20, 3, "self" }, { 90, 2, "self" }, { 160, 4, "self" } },
	widow = { { 20, 2, "self" } },
	carrier = { { 20, 3, "cell" } },
	puppeteer = { { 20, 3, "self" }, { 90, 2, "self" } },
}

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local rows, failed = {}, {}
	local shieldUp = false
	local flayGain = 0
	local charge
	local function firesNear(a)
		local n = 0
		for _, f in ipairs(Map.ActorsInCircle(a.CenterPosition, WDist.FromCells(1) + WDist.New(512))) do
			if f.Type == "flame-patch-blue" and not f.IsDead then n = n + 1 end
		end
		return n
	end
	for _, t in ipairs(castes) do
		local x = xenos.GetActorsByType(t)[1]
		x.Stance = "HoldFire"
		rows[t] = { xeno = x, y = x.Location.Y }
	end
	for _, m in ipairs(marines.GetActorsByType("rifleman")) do
		m.Stance = "HoldFire"
		for _, r in pairs(rows) do
			if r.y == m.Location.Y then r.marine = m; r.hp = m.Health end
		end
	end

	for t, steps in pairs(plan) do
		for _, step in ipairs(steps) do
			Trigger.AfterDelay(step[1], function()
				local r = rows[t]
				local ok
				local before = r.xeno.Plasma
				local fires = t == "pyrogen" and step[2] == 4 and firesNear(r.marine) or 0
				if step[3] == "marine" then
					ok = r.xeno.UseAbilityAt(step[2], r.marine.Location)
				elseif step[3] == "cell" then
					ok = r.xeno.UseAbilityAt(step[2], CPos.New(r.xeno.Location.X - 2, r.xeno.Location.Y))
				else
					ok = r.xeno.UseAbility(step[2])
				end
				if not ok then table.insert(failed, t .. " slot " .. step[2] .. " at " .. step[1]) end
				if t == "warlock" and step[2] == 2 then shieldUp = r.xeno.AbilityActive(2) end
				if t == "puppeteer" and step[2] == 2 then flayGain = r.xeno.Plasma - before end
				if t == "pyrogen" and step[2] == 4 then
					-- Fire Charge costs 20 plasma; the flames it eats around its target must give back more than that.
					charge = { fires = fires, left = 0, net = r.xeno.Plasma - before + 20 }
					-- The eaten flames go at the end of the tick: count what is left a moment later.
					Trigger.AfterDelay(2, function() charge.left = firesNear(r.marine) end)
				end
			end)
		end
	end

	local sprung = false
	local function watchTrap(ticks)
		if #xenos.GetActorsByType("facehugger") > 0 then sprung = true return end
		if ticks < 520 then Trigger.AfterDelay(10, function() watchTrap(ticks + 10) end) end
	end
	Trigger.AfterDelay(240, function()
		local r = rows.carrier
		r.marine.Move(CPos.New(r.xeno.Location.X - 2, r.xeno.Location.Y + 1))
		watchTrap(240)
	end)

	Trigger.AfterDelay(530, function()
		local bad = {}
		if not sprung then table.insert(bad, "the trap did not spring") end
		for _, f in ipairs(failed) do table.insert(bad, f .. " refused") end
		for _, t in ipairs(hurtCastes) do
			if rows[t].marine.Health >= rows[t].hp then table.insert(bad, t .. " did not hurt its marine") end
		end
		if #xenos.GetActorsByType("spiderling") < 1 then table.insert(bad, "no spiderling") end
		if #xenos.GetActorsByType("hugger-trap") < 1 then table.insert(bad, "no hugger trap") end
		if not shieldUp then table.insert(bad, "warlock's shield was not up") end
		if not charge or charge.fires == 0 or charge.left > 0 or charge.net <= 0 then
			table.insert(bad, "Fire Charge did not eat the flames (" .. (charge and (charge.fires .. " before, " .. charge.left .. " after, plasma back " .. charge.net) or "not used") .. ")")
		end
		if flayGain <= 0 then table.insert(bad, "Flay gave the puppeteer no biomass (plasma " .. flayGain .. ")") end
		print("TEST caste-kits " .. (#bad == 0 and "PASS" or "FAIL") .. " (" .. (#bad == 0 and "all abilities worked" or table.concat(bad, "; ")) .. ")")
	end)
end
