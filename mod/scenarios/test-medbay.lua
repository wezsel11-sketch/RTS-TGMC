-- Scenario test: a medbay heals wounded marines nearby with nobody giving an order. Prints "TEST medbay PASS" or "TEST medbay FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local patient = marines.GetActorsByType("rifleman")[1]
	patient.Health = 40
	Trigger.AfterDelay(400, function()
		print("TEST medbay " .. (patient.Health > 80 and "PASS" or "FAIL") .. " (patient at " .. patient.Health .. " of " .. patient.MaxHealth .. ")")
	end)
end
