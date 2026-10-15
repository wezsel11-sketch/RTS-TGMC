-- Scenario test: a rifleman's bullets and a spitter's acid, force-fired at map objects, destroy them. Prints "TEST objects-damage PASS" or "TEST objects-damage FAIL".
-- (mapobj-0 and mapobj-1 are the first two generated map objects, whatever they look like.)
WorldLoaded = function()
	local neutral = Player.GetPlayer("Neutral")
	local rifleman = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	local spitter = Player.GetPlayer("Xenos").GetActorsByType("spitter")[1]
	local a, b = neutral.GetActorsByType("mapobj-0")[1], neutral.GetActorsByType("mapobj-1")[1]
	local a0, b0 = a.Health, b.Health
	Trigger.AfterDelay(10, function()
		rifleman.Attack(a, true, true)
		spitter.Attack(b, true, true)
	end)
	Trigger.AfterDelay(500, function()
		local hurtA = a.IsDead or a.Health < a0
		local hurtB = b.IsDead or b.Health < b0
		print("TEST objects-damage " .. ((hurtA and hurtB) and "PASS" or "FAIL") .. " (bullets hurt " .. tostring(hurtA) .. ", acid hurt " .. tostring(hurtB) .. ")")
	end)
end
