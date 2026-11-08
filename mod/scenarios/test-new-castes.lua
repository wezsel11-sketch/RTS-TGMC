-- Scenario test: the castes added from TGMC (units.yaml, "castes from TGMC"). Each stands in its own row with a tough marine
-- (held fire) two cells away and uses its first ability at tick 20; the scorpion just shoots. By tick 150:
--   baneling: burst (it is gone) and its marine was hurt;  defender, beetle, dragon, pyrogen, scorpion, king: their marine was hurt;
--   puppeteer: three puppets stand;  gorger: Feast was used.
-- Prints "TEST new-castes PASS" or "TEST new-castes FAIL" with what failed.
local hurtCastes = { "baneling", "beetle", "dragon", "pyrogen", "scorpion", "king" }

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local rows, used = {}, {}
	local all = { "baneling", "defender", "beetle", "gorger", "puppeteer", "pyrogen", "scorpion", "dragon", "king" }
	for _, t in ipairs(all) do
		local x = xenos.GetActorsByType(t)[1]
		rows[t] = { xeno = x, y = x.Location.Y }
	end
	for _, m in ipairs(marines.GetActorsByType("rifleman")) do
		m.Stance = "HoldFire"
		for _, r in pairs(rows) do
			if r.y == m.Location.Y then r.marine = m; r.hp = m.Health end
		end
	end
	Trigger.AfterDelay(20, function()
		for t, r in pairs(rows) do
			if t == "scorpion" then
				r.xeno.Attack(r.marine, true, true)
			elseif t == "defender" then
				used[t] = r.xeno.UseAbility(2)
			else
				used[t] = r.xeno.UseAbility(1)
			end
		end
	end)
	Trigger.AfterDelay(150, function()
		local bad = {}
		for _, t in ipairs(hurtCastes) do
			if rows[t].marine.Health >= rows[t].hp then table.insert(bad, t .. " did not hurt its marine") end
		end
		if rows.defender.marine.Health >= rows.defender.hp then table.insert(bad, "defender's sweep did not hurt its marine") end
		if not rows.baneling.xeno.IsDead then table.insert(bad, "baneling did not burst") end
		local puppets = #xenos.GetActorsByType("puppet")
		if puppets < 3 then table.insert(bad, "puppeteer raised " .. puppets .. " puppets") end
		if not used.gorger then table.insert(bad, "gorger could not Feast") end
		print("TEST new-castes " .. (#bad == 0 and "PASS" or "FAIL") .. " (" .. (#bad == 0 and "all abilities worked" or table.concat(bad, "; ")) .. ")")
	end)
end
