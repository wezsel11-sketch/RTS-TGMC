-- Scenario test: abilities aimed by a click. A rifleman with a test grenade (slot 7, a ground spot) and a test throw at a unit (slot 8):
-- A) a runner in reach is hit at once; B) a runner out of reach is hit after the rifleman walks into reach; C) a unit-aimed use whose
-- target dies before the rifleman gets there is dropped, and the ability is still ready (no cooldown spent).
-- Prints "TEST ability-aim PASS" or "TEST ability-aim FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local rifleman = marines.GetActorsByType("rifleman")[1]
	rifleman.Stance = "HoldFire"
	local runners = xenos.GetActorsByType("runner")
	Utils.Do(runners, function(r) r.Stance = "HoldFire" end)
	local near, far, doomed
	for _, r in ipairs(runners) do
		if r.Location.Y > 15 then doomed = r elseif r.Location.X < 12 then near = r else far = r end
	end
	local nearHp, farHp, farCell = near.Health, far.Health, far.Location
	local a, b, c = false, false, false
	local usedA, usedB, usedC

	Trigger.AfterDelay(10, function() usedA = rifleman.UseAbilityAt(7, near.Location) end)
	Trigger.AfterDelay(40, function() a = usedA and (near.IsDead or near.Health < nearHp) end)
	Trigger.AfterDelay(70, function() usedB = rifleman.UseAbilityAt(7, farCell) end)
	Trigger.AfterDelay(330, function()
		local dx, dy = rifleman.Location.X - farCell.X, rifleman.Location.Y - farCell.Y
		b = usedB and (far.IsDead or far.Health < farHp) and dx * dx + dy * dy <= 25
		usedC = rifleman.UseAbilityOn(8, doomed)
	end)
	Trigger.AfterDelay(335, function() doomed.Kill() end)
	Trigger.AfterDelay(500, function()
		c = usedC and rifleman.AbilityReady(8)
		print("TEST ability-aim " .. ((a and b and c) and "PASS" or "FAIL") .. " (A " .. tostring(a) .. ", B " .. tostring(b) .. ", C " .. tostring(c) .. ")")
	end)
end
