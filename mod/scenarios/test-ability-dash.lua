-- Scenario test: a dash (a charge, a pounce) aimed at a spot. A) on open ground the rifleman dashes 5 cells and hurts the runner beside
-- his path; B) a barricade 3 cells ahead stops him on the cell before it; C) aimed past the map edge he stops on the edge, not off it.
-- Prints "TEST ability-dash PASS" or "TEST ability-dash FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local runner = Player.GetPlayer("Xenos").GetActorsByType("runner")[1]
	runner.Stance = "HoldFire"
	local r = {}
	for _, a in ipairs(marines.GetActorsByType("rifleman")) do
		a.Stance = "HoldFire"
		if a.Location.Y == 4 then r.a = a elseif a.Location.Y == 10 then r.b = a else r.c = a end
	end
	local hp = runner.Health
	local used = {}
	Trigger.AfterDelay(10, function()
		used.a = r.a.UseAbilityAt(8, CPos.New(9, 4))
		used.b = r.b.UseAbilityAt(8, CPos.New(9, 10))
		used.c = r.c.UseAbilityAt(8, CPos.New(40, 16))
	end)
	Trigger.AfterDelay(60, function()
		local a = used.a and r.a.Location.X >= 8 and (runner.IsDead or runner.Health < hp)
		local b = used.b and r.b.Location.X == 6
		local c = used.c and not r.c.IsDead and r.c.Location.X >= 29 and r.c.Location.X <= 31
		print("TEST ability-dash " .. ((a and b and c) and "PASS" or "FAIL") .. " (A " .. tostring(a) .. " at " .. r.a.Location.X
			.. ", B " .. tostring(b) .. " at " .. r.b.Location.X .. ", C " .. tostring(c) .. " at " .. r.c.Location.X .. ")")
	end)
end
