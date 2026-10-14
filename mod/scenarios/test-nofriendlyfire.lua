-- Scenario test: with the lobby's friendly fire option switched off, a blast hurts only the enemy. Same layout as
-- test-explosive.lua. Prints "TEST nofriendlyfire PASS" or "TEST nofriendlyfire FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local target = xenos.GetActorsByType("crusher")[1]
	target.Stance = "HoldFire"
	local shooter, bystander
	for _, d in ipairs(marines.GetActorsByType("demolitionist")) do
		if d.Location.X == 10 then
			shooter = d
		else
			bystander = d
		end
	end
	local rifleman = marines.GetActorsByType("rifleman")[1]
	rifleman.Stance = "HoldFire"
	bystander.Stance = "HoldFire"
	local targetMax = target.MaxHealth

	Trigger.AfterDelay(25, function()
		shooter.Attack(target)
	end)

	Trigger.AfterDelay(150, function()
		local hurtFriends = rifleman.IsDead or rifleman.Health < rifleman.MaxHealth or bystander.Health < bystander.MaxHealth
		local hurtEnemy = target.IsDead or target.Health < targetMax
		print("TEST nofriendlyfire " .. ((not hurtFriends and hurtEnemy) and "PASS" or "FAIL") ..
			" (friends hurt=" .. tostring(hurtFriends) .. ", enemy hurt=" .. tostring(hurtEnemy) .. ")")
	end)
end
