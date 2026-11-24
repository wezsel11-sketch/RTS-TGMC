-- Scenario test: what the newer xeno abilities do, one caste per row of the map (every xeno has plasma to spare, marines hold fire
-- and are tough). Grapple Toss and Unrelenting Force throw a marine; Earth Riser raises a pillar; Mirage makes decoys; Regenerate
-- Skin, Transfusion and the Queen's Heal mend; Organic Bomb spends a puppet; a burrowed widow does not move; Grab hurts.
-- Prints "TEST xeno-kit2 PASS" or "TEST xeno-kit2 FAIL (what failed)".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	-- The primordial abilities need their upgrades.
	Actor.Create("upgrade-primordial-1", true, { Owner = xenos })
	Actor.Create("upgrade-primordial-2", true, { Owner = xenos })
	local marines = Player.GetPlayer("Marines")
	for _, a in ipairs(xenos.GetActors()) do if a.HasProperty("Stance") then a.Stance = "HoldFire" end end
	local rifles = marines.GetActorsByType("rifleman")
	for _, a in ipairs(rifles) do a.Stance = "HoldFire" end
	local one = function(t) return xenos.GetActorsByType(t)[1] end
	local rifleAt = function(x, y)
		for _, a in ipairs(rifles) do if a.Location.X == x and a.Location.Y == y then return a end end
	end
	local far = function(a, from) return math.max(math.abs(a.Location.X - from.X), math.abs(a.Location.Y - from.Y)) end
	local half = function(a) a.Health = math.floor(a.MaxHealth / 2) return a.Health end

	local tossed, shovedW, shovedE, grabbed = rifleAt(9, 4), rifleAt(7, 7), rifleAt(9, 7), rifleAt(25, 6)
	local tossed0, shovedW0, shovedE0, grabbed0 = tossed.Location, shovedW.Location, shovedE.Location, grabbed.Health
	local defender, runner, drone, widow, puppeteer = one("defender"), one("runner"), one("drone"), one("widow"), one("puppeteer")
	local defender0, runner0, drone0 = half(defender), half(runner), half(drone)
	local widow0 = widow.Location
	local used, bad = {}, {}
	local puppets, afterBomb

	Trigger.AfterDelay(10, function()
		used.toss = one("warrior").UseAbility(5)
		used.force = one("shrike").UseAbility(3)
		used.riser = one("behemoth").UseAbilityAt(3, CPos.New(11, 10))
		used.mirage = one("hunter").UseAbility(5)
		used.regen = defender.UseAbility(5)
		used.transfusion = one("gorger").UseAbilityOn(3, runner)
		used.heal = one("queen").UseAbilityOn(3, drone)
		used.puppets = puppeteer.UseAbility(1)
		used.burrow = widow.UseAbility(4)
		used.grab = one("dragon").UseAbility(4)
	end)
	Trigger.AfterDelay(20, function()
		widow.Move(CPos.New(widow0.X + 5, widow0.Y))
	end)
	Trigger.AfterDelay(40, function()
		puppets = #xenos.GetActorsByType("puppet")
		used.bomb = puppeteer.UseAbility(5)
	end)
	Trigger.AfterDelay(45, function() afterBomb = #xenos.GetActorsByType("puppet") end)
	Trigger.AfterDelay(120, function()
		local check = function(name, ok, detail) if not ok then bad[#bad + 1] = name .. " (" .. detail .. ")" end end
		for name, ok in pairs(used) do check("use " .. name, ok, "refused") end
		check("toss", far(tossed, tossed0) >= 4, far(tossed, tossed0) .. " cells")
		check("force", math.max(far(shovedW, shovedW0), far(shovedE, shovedE0)) >= 3, far(shovedW, shovedW0) .. " and " .. far(shovedE, shovedE0) .. " cells")
		check("riser", #xenos.GetActorsByType("earth-pillar") == 1, #xenos.GetActorsByType("earth-pillar") .. " pillars")
		check("mirage", #xenos.GetActorsByType("mirage-decoy") >= 1, "no decoy")
		check("regen", defender.Health >= defender0 + 50, defender0 .. " to " .. defender.Health)
		check("transfusion", runner.Health > runner0, runner0 .. " to " .. runner.Health)
		check("heal", drone.Health > drone0, drone0 .. " to " .. drone.Health)
		check("bomb", puppets == 3 and afterBomb == 2, tostring(puppets) .. " puppets, then " .. tostring(afterBomb))
		check("burrow", far(widow, widow0) == 0, far(widow, widow0) .. " cells moved")
		check("grab", grabbed.Health < grabbed0, grabbed0 .. " to " .. grabbed.Health)
		print("TEST xeno-kit2 " .. (#bad == 0 and "PASS" or "FAIL (" .. table.concat(bad, "; ") .. ")"))
	end)
end
