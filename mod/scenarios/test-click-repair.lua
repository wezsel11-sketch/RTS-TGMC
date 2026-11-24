-- Scenario test: what a plain right-click gives the player, which the other tests never ask (they order through the script).
-- An engineer on its own damaged miner and on a free ore field must get the attack order with the repair cursor; a drone on a free
-- field must get it too (the resin that corrupts). A rifleman on a free field must get no attack order.
-- Prints "TEST click-repair PASS" or "TEST click-repair FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local neutral = Player.GetPlayer("Neutral")
	local engineer = marines.GetActorsByType("engineer")[1]
	local rifleman = marines.GetActorsByType("rifleman")[1]
	local drone = xenos.GetActorsByType("drone")[1]
	local miner = marines.GetActorsByType("miner")[1]
	local field = neutral.GetActorsByType("miner-field")[1]
	Trigger.AfterDelay(10, function()
		miner.Health = math.floor(miner.MaxHealth / 2)
	end)
	Trigger.AfterDelay(20, function()
		local a = engineer.ClickOrder(miner)
		local b = engineer.ClickOrder(field)
		local c = drone.ClickOrder(field)
		local d = rifleman.ClickOrder(field)
		local ok = a:find("^Attack|repair") and b:find("^Attack|repair") and c:find("^Attack|repair") and not d:find("^Attack")
		print("TEST click-repair " .. (ok and "PASS" or "FAIL") .. " (engineer on miner " .. a .. ", engineer on field " .. b ..
			", drone on field " .. c .. ", rifleman on field " .. d .. ")")
	end)
end
