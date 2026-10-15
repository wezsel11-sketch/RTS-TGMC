-- Scenario test: riflemen shoot while walking past an enemy, snipers and machine gunners do not. Prints "TEST movefire PASS" or "TEST movefire FAIL".
local reported = false

WorldLoaded = function()
	local marines, xenos = Player.GetPlayer("Marines"), Player.GetPlayer("Xenos")
	local rifle, sniper = marines.GetActorsByType("rifleman")[1], marines.GetActorsByType("sniper")[1]
	local silos = xenos.GetActorsByType("crusher")
	local rifleSilo, sniperSilo = silos[1], silos[2]
	local r0, s0 = rifleSilo.Health, sniperSilo.Health
	rifle.Move(CPos.New(40, 10))
	sniper.Move(CPos.New(40, 20))
	-- Polled, because a walking marine fires only when a shot happens to be due while an enemy is in range, so the first hit may take a while.
	local function poll(ticks)
		if reported then return end
		local rifleHit = rifleSilo.Health < r0
		local sniperHit = sniperSilo.Health < s0
		if sniperHit then
			reported = true
			print("TEST movefire FAIL (the sniper hit while walking)")
		elseif rifleHit then
			reported = true
			print("TEST movefire PASS (rifle silo " .. r0 .. " -> " .. rifleSilo.Health .. ", sniper silo untouched)")
		elseif ticks >= 400 then
			reported = true
			print("TEST movefire FAIL (the rifleman never hit while walking)")
		else
			Trigger.AfterDelay(10, function() poll(ticks + 10) end)
		end
	end
	Trigger.AfterDelay(10, function() poll(10) end)
end
