-- Scenario test: weeds die with the node that grew them. Prints "TEST wither PASS" or "TEST wither FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local node = xenos.GetActorsByType("weed-node")[1]
	local before = 0
	Trigger.AfterDelay(700, function()
		before = #xenos.GetActorsByType("weeds")
		node.Kill()
	end)
	Trigger.AfterDelay(1000, function()
		local after = #xenos.GetActorsByType("weeds")
		print("TEST wither " .. ((before >= 3 and after == 0) and "PASS" or "FAIL") .. " (" .. before .. " weeds -> " .. after .. ")")
	end)
end
