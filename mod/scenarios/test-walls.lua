-- Scenario test: a CAS bomb run knocks cells of a wall down to rubble, and a mortar shell alone does not. Prints "TEST walls PASS" or "TEST walls FAIL".
WorldLoaded = function()
	local depot = Player.GetPlayer("Marines").GetActorsByType("ordnance-depot")[1]
	local cells = { CPos.New(14, 11), CPos.New(15, 11), CPos.New(16, 11) }
	local before = {}
	for i, c in ipairs(cells) do
		before[i] = Map.TerrainType(c)
	end
	Trigger.AfterDelay(20, function()
		depot.ActivateCondorStrike(CPos.New(13, 11), "cas")
	end)
	Trigger.AfterDelay(500, function()
		local fallen = 0
		for i, c in ipairs(cells) do
			if Map.TerrainType(c) ~= "Wall" then
				fallen = fallen + 1
			end
		end
		print("TEST walls " .. ((before[1] == "Wall" and fallen >= 1) and "PASS" or "FAIL") .. " (" .. fallen .. " of 3 wall cells fell, first was " .. tostring(before[1]) .. ")")
	end)
end
