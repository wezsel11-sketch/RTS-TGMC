-- Scenario test: a hunter's Silence stops a squad leader's abilities for its five seconds. Before it the leader's Smoke is ready, while it
-- lasts it is refused, and once it wears off it works again.
-- Prints "TEST ability-silence PASS" or "TEST ability-silence FAIL".
WorldLoaded = function()
	local leader = Player.GetPlayer("Marines").GetActorsByType("squad_leader")[1]
	local hunter = Player.GetPlayer("Xenos").GetActorsByType("hunter")[1]
	leader.Stance = "HoldFire"
	hunter.Stance = "HoldFire"
	local before, during, after
	Trigger.AfterDelay(10, function()
		before = leader.AbilityReady(1)
		hunter.UseAbilityAt(4, leader.Location)
	end)
	Trigger.AfterDelay(20, function() during = leader.UseAbility(1) end)
	Trigger.AfterDelay(160, function()
		after = leader.UseAbility(1)
		local ok = before and during == false and after
		print("TEST ability-silence " .. (ok and "PASS" or "FAIL") .. " (before " .. tostring(before) .. ", during " .. tostring(during) .. ", after " .. tostring(after) .. ")")
	end)
end
