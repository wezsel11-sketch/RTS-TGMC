-- Scenario test: runners attack a marine sentry turret. The turret holds when every runner dies and the turret stands.
-- Prints the outcome after 1500 ticks: "TEST turret-holds PASS|FAIL (runners left N, turret hp H of M)".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local turret = marines.GetActorsByType("sentry-turret")[1]
	local runners = xenos.GetActorsByType("runner")
	Trigger.AfterDelay(10, function()
		for _, r in ipairs(runners) do
			r.Attack(turret, true, false)
		end
	end)
	Trigger.AfterDelay(1500, function()
		local left = 0
		for _, r in ipairs(runners) do
			if not r.IsDead then
				left = left + 1
			end
		end
		local standing = not turret.IsDead
		local hp = standing and turret.Health or 0
		print("TEST turret-holds " .. ((standing and left == 0) and "PASS" or "FAIL") .. " (runners left " .. left .. ", turret hp " .. hp .. " of " .. (standing and turret.MaxHealth or 0) .. ")")
	end)
end
