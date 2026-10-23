-- Scenario test: a leader's order is a yell that buffs the marines around him. Two squad leaders yell the same order (slot 8): the
-- rifleman 3 cells away gets it once (no stacking), the one 10 cells away does not, and it wears off after its time.
-- Prints "TEST ability-aura PASS" or "TEST ability-aura FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local leaders = marines.GetActorsByType("squad_leader")
	local near, far
	for _, r in ipairs(marines.GetActorsByType("rifleman")) do
		if r.Location.X < 14 then near = r else far = r end
	end
	local used, during
	Trigger.AfterDelay(10, function()
		used = leaders[1].UseAbility(8) and leaders[2].UseAbility(8)
		during = near.HasAuraCondition("order-move") and not far.HasAuraCondition("order-move") and near.AuraStacks("order-move") == 1
	end)
	Trigger.AfterDelay(180, function()
		local after = not near.HasAuraCondition("order-move")
		print("TEST ability-aura " .. ((used and during and after) and "PASS" or "FAIL") .. " (used " .. tostring(used) .. ", during " .. tostring(during) .. ", worn off " .. tostring(after) .. ")")
	end)
end
