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
	Trigger.AfterDelay(120, function()
		if reported then return end
		reported = true
		local rifleHit = rifleSilo.Health < r0
		local sniperHit = sniperSilo.Health < s0
		if rifleHit and not sniperHit then
			print("TEST movefire PASS (rifle silo " .. r0 .. " -> " .. rifleSilo.Health .. ", sniper silo untouched)")
		else
			print("TEST movefire FAIL (rifle hit: " .. tostring(rifleHit) .. ", sniper hit: " .. tostring(sniperHit) .. ")")
		end
	end)
end
