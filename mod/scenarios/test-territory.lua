-- Scenario test: weeds as territory.
-- Gate: a warrior cannot evolve into a praetorian (tier 3) with three weed nodes, and can once a fourth stands; when a node
-- dies the gate shuts again.
-- Fed: a corrupted miner with weeds beside it pays 11 per 50 ticks, and 7 once the weeds are gone (40 less over 500 ticks).
-- Burn: a fire on a weed cell kills it; a weed cell away from the fire lives.
-- Prints "TEST territory PASS" or "TEST territory FAIL (what failed)".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	xenos.Cash = 5000
	-- The marine is only there so the match does not end: left to fire he would knock the miner down.
	Player.GetPlayer("Marines").GetActorsByType("rifleman")[1].Stance = "HoldFire"
	local weedAt = function(x, y)
		for _, w in ipairs(xenos.GetActorsByType("weeds")) do
			if w.Location.X == x and w.Location.Y == y then return w end
		end
	end
	local feeder, burned, spared = weedAt(9, 18), weedAt(20, 14), weedAt(26, 14)
	local bad = {}
	local early, fedFrom, fedGain, starvedFrom

	Trigger.AfterDelay(20, function() xenos.GetActorsByType("warrior")[1].Evolve() end)
	Trigger.AfterDelay(50, function()
		early = #xenos.GetActorsByType("praetorian")
		Actor.Create("weed-node", true, { Owner = xenos, Location = CPos.New(14, 10) })
	end)
	Trigger.AfterDelay(70, function() xenos.GetActorsByType("warrior")[1].Evolve() end)
	Trigger.AfterDelay(200, function()
		if early ~= 0 then bad[#bad + 1] = "evolved with three nodes" end
		if #xenos.GetActorsByType("praetorian") ~= 1 then bad[#bad + 1] = "not evolved with four nodes" end
		if burned ~= nil and not burned.IsDead then bad[#bad + 1] = "weed under the fire lives" end
		if spared == nil or spared.IsDead then bad[#bad + 1] = "weed away from the fire died" end
		fedFrom = xenos.Cash
	end)
	Trigger.AfterDelay(700, function()
		fedGain = xenos.Cash - fedFrom
		feeder.Destroy()
		-- A node dies: three are left, and the gate must be shut again.
		xenos.GetActorsByType("weed-node")[1].Kill()
	end)
	Trigger.AfterDelay(720, function()
		if xenos.HasPrerequisites({ "hive-territory-1" }) then bad[#bad + 1] = "gate still open with three nodes after one died" end
	end)
	-- The miner looks for weeds once a second: start the second count after it has noticed.
	Trigger.AfterDelay(760, function() starvedFrom = xenos.Cash end)
	Trigger.AfterDelay(1260, function()
		local starvedGain = xenos.Cash - starvedFrom
		local less = fedGain - starvedGain
		if less < 30 or less > 50 then bad[#bad + 1] = "fed " .. fedGain .. ", starved " .. starvedGain .. " over 500 ticks (expected 40 less)" end
		print("TEST territory " .. (#bad == 0 and "PASS" or "FAIL (" .. table.concat(bad, "; ") .. ")"))
	end)
end
