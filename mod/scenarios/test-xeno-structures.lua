-- Scenario test: every melee xeno caste can claw down marine structures. A hunter and a runner are each ordered to attack a
-- barricade and a sentry turret (held fire). After 400 ticks every structure has lost health.
-- Prints "TEST xeno-structures PASS" or "TEST xeno-structures FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local targets = {}
	for _, t in ipairs({ "cade", "sentry-turret" }) do
		for _, a in ipairs(marines.GetActorsByType(t)) do
			if a.Type == "sentry-turret" then a.Stance = "HoldFire" end
			targets[#targets + 1] = { actor = a, hp = a.Health }
		end
	end
	table.sort(targets, function(a, b) return a.actor.Location.Y < b.actor.Location.Y end)
	local attackers = {}
	for _, t in ipairs({ "hunter", "runner" }) do
		for _, a in ipairs(xenos.GetActorsByType(t)) do attackers[#attackers + 1] = a end
	end
	table.sort(attackers, function(a, b) return a.Location.Y < b.Location.Y end)
	-- Orders given on the first tick are dropped: units cannot take them yet.
	Trigger.AfterDelay(10, function()
		for i, a in ipairs(attackers) do a.Attack(targets[i].actor, true, true) end
	end)
	Trigger.AfterDelay(400, function()
		local ok, parts = true, {}
		for i, t in ipairs(targets) do
			local lost = t.hp - (t.actor.IsDead and 0 or t.actor.Health)
			parts[#parts + 1] = attackers[i].Type .. " vs " .. t.actor.Type .. ": " .. lost .. " lost"
			if lost <= 0 then ok = false end
		end
		print("TEST xeno-structures " .. (ok and "PASS" or "FAIL") .. " (" .. table.concat(parts, ", ") .. ")")
	end)
end
