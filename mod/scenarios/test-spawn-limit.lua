-- Scenario test: an ability's SpawnLimit (ActiveAbility in CasteAbilities.cs). The widow births a spiderling ten times, with no cooldown
-- or plasma cost; only five may live at once, and the ability is not ready while five do. When one dies she may birth again.
-- Prints "TEST spawn-limit PASS" or "TEST spawn-limit FAIL" with what went wrong.
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local widow = xenos.GetActorsByType("widow")[1]
	for i = 1, 10 do
		Trigger.AfterDelay(i * 3, function() widow.UseAbility(2) end)
	end
	Trigger.AfterDelay(40, function()
		local bad = {}
		local lings = xenos.GetActorsByType("spiderling")
		if #lings ~= 5 then table.insert(bad, #lings .. " spiderlings, not 5") end
		if widow.AbilityReady(2) then table.insert(bad, "ready with five alive") end
		if #lings > 0 then lings[1].Kill() end
		Trigger.AfterDelay(3, function()
			if not widow.UseAbility(2) then table.insert(bad, "refused after one died") end
			Trigger.AfterDelay(3, function()
				local n = #xenos.GetActorsByType("spiderling")
				if n ~= 5 then table.insert(bad, n .. " spiderlings after the rebirth, not 5") end
				print("TEST spawn-limit " .. (#bad == 0 and "PASS" or "FAIL (" .. table.concat(bad, "; ") .. ")"))
			end)
		end)
	end)
end
