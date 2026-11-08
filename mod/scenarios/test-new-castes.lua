-- Scenario test: the castes added from TGMC (units.yaml, "castes from TGMC") and the castes whose kits follow TGMC's (mantis,
-- behemoth, hivelord, king). Each stands in its own row with a tough marine (held fire) two cells away and uses its first ability
-- at tick 20 (the defender its sweep, the behemoth Geocrush); the scorpion just shoots. At tick 90 the king Petrifies, the
-- behemoth Landslides and the hivelord infuses the wounded nymph beside it. By tick 150:
--   baneling: burst (it is gone) and its marine was hurt;  defender, beetle, dragon, pyrogen, scorpion, king, mantis, behemoth:
--   their marine was hurt;  puppeteer: three puppets stand;  every one's ability was used;  king: Petrify, behemoth: Geocrush and Landslide
--   were used;  hivelord: the nymph has healed.
-- Prints "TEST new-castes PASS" or "TEST new-castes FAIL" with what failed.
local hurtCastes = { "baneling", "beetle", "dragon", "pyrogen", "scorpion", "king", "mantis", "behemoth" }

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local rows, used = {}, {}
	local all = { "baneling", "defender", "beetle", "gorger", "puppeteer", "pyrogen", "scorpion", "dragon", "king", "mantis", "behemoth" }
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
	local hivelord = xenos.GetActorsByType("hivelord")[1]
	local nymph = xenos.GetActorsByType("nymph")[1]
	nymph.Stance = "HoldFire"
	hivelord.Stance = "HoldFire"
	local woundedHp
	Trigger.AfterDelay(20, function()
		for t, r in pairs(rows) do
			if t == "scorpion" then
				r.xeno.Attack(r.marine, true, true)
			elseif t == "defender" or t == "behemoth" then
				used[t] = r.xeno.UseAbility(2)
			else
				used[t] = r.xeno.UseAbility(1)
			end
		end
		nymph.Health = math.floor(nymph.MaxHealth / 4)
		woundedHp = nymph.Health
	end)
	Trigger.AfterDelay(90, function()
		used.petrify = rows.king.xeno.UseAbility(2)
		used.landslide = rows.behemoth.xeno.UseAbility(1)
		used.infusion = hivelord.UseAbilityOn(1, nymph)
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
		for _, t in ipairs(all) do
			if t ~= "scorpion" and not used[t] then table.insert(bad, t .. " could not use its ability") end
		end
		if not used.petrify then table.insert(bad, "king could not Petrify") end
		if not used.landslide then table.insert(bad, "behemoth could not Landslide") end
		if not used.infusion then table.insert(bad, "hivelord could not infuse") end
		if nymph.Health <= woundedHp then table.insert(bad, "infused nymph did not heal (" .. nymph.Health .. ")") end
		print("TEST new-castes " .. (#bad == 0 and "PASS" or "FAIL") .. " (" .. (#bad == 0 and "all abilities worked" or table.concat(bad, "; ")) .. ")")
	end)
end
