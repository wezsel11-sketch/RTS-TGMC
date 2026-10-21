-- Scenario test: a friendly blast hurts an ally (friendly fire on) but must not raise the under-attack alert for the owner.
-- Same layout as test-explosive.lua: a demolitionist fires at a Hold Fire crusher standing next to a rifleman. The crusher never
-- attacks, so any alert would come from the friendly damage. Prints "TEST friendly-fire-alert PASS" or "TEST friendly-fire-alert FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local target = Player.GetPlayer("Xenos").GetActorsByType("crusher")[1]
	target.Stance = "HoldFire"
	local shooter
	for _, d in ipairs(marines.GetActorsByType("demolitionist")) do
		if d.Location.X == 10 then shooter = d else d.Stance = "HoldFire" end
	end
	local rifleman = marines.GetActorsByType("rifleman")[1]
	rifleman.Stance = "HoldFire"
	local rifleMax = rifleman.MaxHealth

	Trigger.AfterDelay(25, function() shooter.Attack(target) end)

	Trigger.AfterDelay(150, function()
		local hurt = rifleman.IsDead or rifleman.Health < rifleMax
		local alerts = marines.EventCount("event-under-attack")
		print("TEST friendly-fire-alert " .. ((hurt and alerts == 0) and "PASS" or "FAIL") ..
			" (rifleman hurt by the blast " .. tostring(hurt) .. ", alerts " .. alerts .. ")")
	end)
end
