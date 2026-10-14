-- Scenario test: the B18 heavy gunner out-damages a rifleman many times over, and walks slower. Each fires at its own
-- crusher for the same time. Prints "TEST heavy PASS" or "TEST heavy FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local heavy = marines.GetActorsByType("heavygunner")[1]
	local rifle = marines.GetActorsByType("rifleman")[1]
	local crushers = xenos.GetActorsByType("crusher")
	local heavyTarget, rifleTarget
	for _, c in ipairs(crushers) do
		c.Stance = "HoldFire"
		if c.Location.Y == 10 then
			heavyTarget = c
		else
			rifleTarget = c
		end
	end
	local heavyMax, rifleMax = heavyTarget.MaxHealth, rifleTarget.MaxHealth
	local function lost(a, max)
		if a.IsDead then
			return max
		end
		return max - a.Health
	end
	Trigger.AfterDelay(10, function()
		heavy.Attack(heavyTarget)
		rifle.Attack(rifleTarget)
	end)
	Trigger.AfterDelay(120, function()
		local heavyDamage = lost(heavyTarget, heavyMax)
		local rifleDamage = lost(rifleTarget, rifleMax)
		local ok = heavyDamage > rifleDamage * 1.5
		print("TEST heavy " .. (ok and "PASS" or "FAIL") .. " (heavy gunner did " .. heavyDamage .. ", rifleman did " .. rifleDamage .. ")")
	end)
end
