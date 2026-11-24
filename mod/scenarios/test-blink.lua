-- Scenario test: the SOM Blink Assault Veteran's blink drive. A hunter stands six cells away; the blink (slot 2) must put the
-- veteran within two cells of it at once. Prints "TEST blink PASS" or "TEST blink FAIL".
WorldLoaded = function()
	local blade = Player.GetPlayer("Marines").GetActorsByType("som_blademan")[1]
	local hunter = Player.GetPlayer("Xenos").GetActorsByType("hunter")[1]
	blade.Stance = "HoldFire"
	hunter.Stance = "HoldFire"
	Trigger.AfterDelay(20, function()
		local from = blade.Location
		local used = blade.UseAbility(2)
		Trigger.AfterDelay(5, function()
			local d = math.max(math.abs(blade.Location.X - hunter.Location.X), math.abs(blade.Location.Y - hunter.Location.Y))
			print("TEST blink " .. ((used and d <= 2) and "PASS" or "FAIL") .. " (used " .. tostring(used) .. ", from " .. tostring(from) ..
				" to " .. tostring(blade.Location) .. ", " .. d .. " cells from the hunter)")
		end)
	end)
end
