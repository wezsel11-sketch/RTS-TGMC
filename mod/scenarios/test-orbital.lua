-- Scenario test: the orbital strike (a support power of the workshop) kills the xenos at the target spot after its warning, and a wall there falls.
-- Prints "TEST orbital PASS" or "TEST orbital FAIL".
WorldLoaded = function()
	local workshop = Player.GetPlayer("Marines").GetActorsByType("workshop")[1]
	local hunters = Player.GetPlayer("Xenos").GetActorsByType("hunter")
	Trigger.AfterDelay(20, function()
		workshop.ActivateCondorStrike(CPos.New(15, 11), "orbital")
	end)
	Trigger.AfterDelay(900, function()
		local dead = 0
		for _, h in ipairs(hunters) do
			if h.IsDead then
				dead = dead + 1
			end
		end
		local wall = Map.TerrainType(CPos.New(15, 11)) ~= "Wall"
		print("TEST orbital " .. ((dead == #hunters and wall) and "PASS" or "FAIL") .. " (" .. dead .. " of " .. #hunters .. " hunters dead, wall fell " .. tostring(wall) .. ")")
	end)
end
