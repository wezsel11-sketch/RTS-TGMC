-- Scenario test: a xeno ability costs plasma. A ravager that starts with 10 plasma is refused Rage, and gets it once the plasma has built up.
-- Prints "TEST plasma PASS" or "TEST plasma FAIL".
WorldLoaded = function()
	local ravager = Player.GetPlayer("Xenos").GetActorsByType("ravager")[1]
	-- The rifleman is only there so the match does not end; left to fire he can kill the ravager before the second try.
	Player.GetPlayer("Marines").GetActorsByType("rifleman")[1].Stance = "HoldFire"
	local early, late
	Trigger.AfterDelay(10, function()
		early = ravager.UseAbility(1)
	end)
	-- A sentinel with no marine in reach: its Neurotoxin is refused and must not cost plasma.
	local sentinel = Player.GetPlayer("Xenos").GetActorsByType("sentinel")[1]
	local kept
	Trigger.AfterDelay(20, function()
		local before = sentinel.Plasma
		sentinel.UseAbility(1)
		kept = sentinel.Plasma >= before
	end)
	Trigger.AfterDelay(400, function()
		late = ravager.UseAbility(1)
		print("TEST plasma " .. ((early == false and late == true and kept) and "PASS" or "FAIL") .. " (early " .. tostring(early) .. ", late " .. tostring(late) .. ", refused use kept plasma " .. tostring(kept) .. ")")
	end)
end
