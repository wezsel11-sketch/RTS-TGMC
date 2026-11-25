-- Scenario test: the xeno stat upgrades do what their numbers say. A rifleman shoots a runner; Carapace I is bought halfway, and
-- each hit must then take about 13 percent less. Then the runner claws the rifleman; Sharper Claws is bought halfway, and each
-- hit must then do about 15 percent more. Prints "TEST xeno-stats PASS" or "TEST xeno-stats FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local rifleman = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	local runner = xenos.GetActorsByType("runner")[1]
	local hits = { shotBefore = {}, shotAfter = {}, clawBefore = {}, clawAfter = {} }
	local phase = "shotBefore"
	runner.Stance = "HoldFire"
	rifleman.Stance = "HoldFire"

	Trigger.OnDamaged(runner, function(_, _, damage)
		if phase == "shotBefore" or phase == "shotAfter" then table.insert(hits[phase], damage) end
	end)
	Trigger.OnDamaged(rifleman, function(_, _, damage)
		if phase == "clawBefore" or phase == "clawAfter" then table.insert(hits[phase], damage) end
	end)

	local function mean(list)
		local sum = 0
		for _, v in ipairs(list) do sum = sum + v end
		return #list > 0 and sum / #list or 0
	end

	Trigger.AfterDelay(10, function() rifleman.Attack(runner, false, true) end)
	Trigger.AfterDelay(310, function()
		Actor.Create("upgrade-carapace-1", true, { Owner = xenos })
		phase = "shotAfter"
	end)
	Trigger.AfterDelay(610, function()
		phase = "clawBefore"
		rifleman.Stop()
		runner.Attack(rifleman, true, true)
	end)
	Trigger.AfterDelay(910, function()
		Actor.Create("upgrade-claws", true, { Owner = xenos })
		phase = "clawAfter"
	end)
	Trigger.AfterDelay(1210, function()
		local shot = mean(hits.shotAfter) / math.max(1, mean(hits.shotBefore))
		local claw = mean(hits.clawAfter) / math.max(1, mean(hits.clawBefore))
		-- Damage is whole points, so a 13 percent cut on a small hit rounds: allow a band around each number.
		local ok = #hits.shotBefore > 2 and #hits.shotAfter > 2 and #hits.clawBefore > 2 and #hits.clawAfter > 2
			and shot >= 0.78 and shot <= 0.92 and claw >= 1.10 and claw <= 1.22
		print("TEST xeno-stats " .. (ok and "PASS" or "FAIL") .. string.format(" (shots %.2f x, %d then %d hits; claws %.2f x, %d then %d hits)",
			shot, #hits.shotBefore, #hits.shotAfter, claw, #hits.clawBefore, #hits.clawAfter))
	end)
end
