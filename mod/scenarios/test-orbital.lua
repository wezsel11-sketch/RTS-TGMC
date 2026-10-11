-- Scenario test (see mod/test_scenarios.sh): the Orbital Strike marker blows up after a moment, killing the enemy in its blast
-- and sparing a friend just outside it. The power itself has no Lua hook, so this drops the marker the power would.
-- Prints "TEST orbital PASS" or "TEST orbital FAIL".
WorldLoaded = function()
	local marines, xenos = Player.GetPlayer("Marines"), Player.GetPlayer("Xenos")
	local target = xenos.GetActorsByType("runner")[1]
	local friend = marines.GetActorsByType("rifleman")[1]
	target.Stance = "HoldFire"
	friend.Stance = "HoldFire"
	Actor.Create("orbital-strike", true, { Owner = marines, Location = CPos.New(10, 10) })
	Trigger.AfterDelay(120, function()
		local friendHurt = friend.IsDead or friend.Health < friend.MaxHealth
		print("TEST orbital " .. ((target.IsDead and not friendHurt) and "PASS" or "FAIL") .. " (the enemy in the blast is " .. (target.IsDead and "dead" or "alive")
			.. ", the friend well outside it is " .. (friendHurt and "hurt" or "unharmed") .. ")")
	end)
end
