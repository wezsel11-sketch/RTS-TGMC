-- Scenario test: an engineer with a damaged cade beside it and a xeno in shotgun reach shoots the xeno before it repairs the cade.
-- Prints "TEST engineer-shoots PASS" or "TEST engineer-shoots FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local cade = marines.GetActorsByType("cade")[1]
	local runner = xenos.GetActorsByType("runner")[1]
	runner.Stance = "HoldFire"
	cade.Health = math.floor(cade.MaxHealth / 2)
	local hp0 = runner.Health
	Trigger.AfterDelay(75, function()
		local hurt = runner.IsDead or runner.Health < hp0
		print("TEST engineer-shoots " .. (hurt and "PASS" or "FAIL") .. " (runner hurt=" .. tostring(hurt) .. ")")
	end)
end
