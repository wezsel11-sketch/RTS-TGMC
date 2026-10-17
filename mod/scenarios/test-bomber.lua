-- Scenario test: the suicide vest. A bomber detonates next to two hunters: after the fuse both hunters are hurt, and the bomber is dead.
-- Prints "TEST bomber PASS" or "TEST bomber FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local bomber = marines.GetActorsByType("bomber")[1]
	local hunters = xenos.GetActorsByType("hunter")
	Trigger.AfterDelay(10, function()
		bomber.UseAbility(1)
	end)
	Trigger.AfterDelay(200, function()
		local hurt = 0
		for _, h in ipairs(hunters) do
			if h.IsDead or h.Health < 3000 then
				hurt = hurt + 1
			end
		end
		print("TEST bomber " .. ((bomber.IsDead and hurt == #hunters) and "PASS" or "FAIL") .. " (bomber dead " .. tostring(bomber.IsDead) .. ", " .. hurt .. " of " .. #hunters .. " hunters hurt)")
	end)
end
