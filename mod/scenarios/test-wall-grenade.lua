-- Scenario test: every explosion chips walls. Three grenadiers lob grenades at a resin wall that stands against a wall of the map (it has 30000 hit
-- points); the wall cell beside it must fall to rubble. Prints "TEST wall-grenade PASS" or "TEST wall-grenade FAIL".
WorldLoaded = function()
	local resin = Player.GetPlayer("Xenos").GetActorsByType("resin-wall")[1]
	local cell = CPos.New(14, 11)
	local before = Map.TerrainType(cell)
	for _, g in ipairs(Player.GetPlayer("Marines").GetActorsByType("grenadier")) do
		g.Attack(resin, false, true)
	end
	Trigger.AfterDelay(1500, function()
		local after = Map.TerrainType(cell)
		print("TEST wall-grenade " .. ((before == "Wall" and after ~= "Wall") and "PASS" or "FAIL") .. " (the cell was " .. tostring(before) .. ", is " .. tostring(after)
			.. "; the resin wall has " .. resin.Health .. " hit points left)")
	end)
end
