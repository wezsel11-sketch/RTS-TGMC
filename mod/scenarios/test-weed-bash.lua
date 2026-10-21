-- Scenario test: a marine bashes a xeno weed node with his rifle butt (nothing else can target it). Three rows, 14 cells apart:
--   y 8:  a rifleman 3 cells from a node, no order     -> he must go and bash it on his own
--   y 22: a rifleman 10 cells from a node, force-fire  -> he must walk up and bash it
--   y 36: a rifleman 10 cells from a node, attack-move to the node's cell (what the marine bot's sweep sends)
-- Prints "TEST weed-bash PASS" or "TEST weed-bash FAIL" after 900 ticks.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local function at(player, type, y)
		for _, a in ipairs(player.GetActorsByType(type)) do
			if a.Location.Y == y then return a end
		end
	end
	local idleMan, idleNode = at(marines, "rifleman", 8), at(xenos, "weed-node", 8)
	local forceMan, forceNode = at(marines, "rifleman", 22), at(xenos, "weed-node", 22)
	local moveMan, moveNode = at(marines, "rifleman", 36), at(xenos, "weed-node", 36)
	local idleMax, forceMax, moveMax = idleNode.MaxHealth, forceNode.MaxHealth, moveNode.MaxHealth

	Trigger.AfterDelay(5, function()
		forceMan.Attack(forceNode, true, true)
		moveMan.AttackMove(moveNode.Location)
	end)

	local function hurt(a, max) return a.IsDead or a.Health < max end
	Trigger.AfterDelay(900, function()
		local r1, r2, r3 = hurt(idleNode, idleMax), hurt(forceNode, forceMax), hurt(moveNode, moveMax)
		print("DBG auto " .. tostring(r1) .. ", force-fire " .. tostring(r2) .. ", attack-move " .. tostring(r3))
		print("TEST weed-bash " .. ((r1 and r2 and r3) and "PASS" or "FAIL"))
	end)
end
