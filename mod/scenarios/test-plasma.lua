-- Scenario test: a xeno ability costs plasma. A ravager that starts with 10 plasma is refused Rage, and gets it once the plasma has built up.
-- Prints "TEST plasma PASS" or "TEST plasma FAIL".
WorldLoaded = function()
	local ravager = Player.GetPlayer("Xenos").GetActorsByType("ravager")[1]
	local early, late
	Trigger.AfterDelay(10, function()
		early = ravager.UseAbility(1)
	end)
	Trigger.AfterDelay(400, function()
		late = ravager.UseAbility(1)
		print("TEST plasma " .. ((early == false and late == true) and "PASS" or "FAIL") .. " (early " .. tostring(early) .. ", late " .. tostring(late) .. ")")
	end)
end
