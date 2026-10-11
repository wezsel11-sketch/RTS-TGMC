-- Scenario test (see mod/test_scenarios.sh): artillery shoots from range, and backs away from what is too close to hit.
-- Each of the marine Mortar Crew and the xeno Boiler gets two idle targets: one six cells away (in the crew's sight, outside
-- its minimum range) and one two cells away (inside it). Targets are told to hold fire so they neither shoot back nor charge.
-- The crew with the far target fires where it stands; the crew with the near target must first walk out of the dead zone (the
-- engine moves an attacker to a spot between its minimum and maximum range) and then fires too.
-- Prints "TEST artillery PASS" or "TEST artillery FAIL" with what each target lost and how far each crew moved.
local function at(player, type, x, y)
	for _, a in ipairs(player.GetActorsByType(type)) do
		if a.Location.X == x and a.Location.Y == y then
			return a
		end
	end
end

WorldLoaded = function()
	local marines, xenos = Player.GetPlayer("Marines"), Player.GetPlayer("Xenos")
	local mortar, mortarFar, mortarNear = at(marines, "mortar-crew", 3, 3), at(xenos, "runner", 9, 3), at(xenos, "runner", 5, 10)
	local mortarNearCrew = at(marines, "mortar-crew", 3, 10)
	local boiler, boilerFar, boilerNear = at(xenos, "boiler", 25, 3), at(marines, "rifleman", 31, 3), at(marines, "rifleman", 27, 10)
	local boilerNearCrew = at(xenos, "boiler", 25, 10)
	local maxHealth = {}
	for _, a in ipairs({ mortarFar, mortarNear, boilerFar, boilerNear }) do
		a.Stance = "HoldFire"
		maxHealth[a] = a.MaxHealth
	end

	local startNear = { mortarNearCrew.Location, boilerNearCrew.Location }
	local startFar = { mortar.Location, boiler.Location }
	Trigger.AfterDelay(400, function()
		local lost = function(a) return a.IsDead and maxHealth[a] or (maxHealth[a] - a.Health) end
		local mf, mn, bf, bn = lost(mortarFar), lost(mortarNear), lost(boilerFar), lost(boilerNear)
		local moved = function(a, from) return (a.Location - from).Length end
		local mortarBack, boilerBack = moved(mortarNearCrew, startNear[1]), moved(boilerNearCrew, startNear[2])
		local mortarStay, boilerStay = moved(mortar, startFar[1]), moved(boiler, startFar[2])
		local ok = mf >= 30 and mn >= 30 and bf >= 30 and bn >= 30 and mortarBack >= 1 and boilerBack >= 1 and mortarStay <= 1 and boilerStay <= 1
		print("TEST artillery " .. (ok and "PASS" or "FAIL") .. " (mortar: far target lost " .. mf .. ", near target lost " .. mn .. ", its crew backed off "
			.. mortarBack .. " cells and the other crew " .. mortarStay .. "; boiler: far target lost " .. bf .. ", near target lost " .. bn
			.. ", its boiler backed off " .. boilerBack .. " cells and the other " .. boilerStay .. ")")
	end)
end
