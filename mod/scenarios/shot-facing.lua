-- Not a test: marines and xenos walk off in four directions so a screenshot can show which way each sprite faces.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local dirs = { N = CVec.New(0, -5), E = CVec.New(5, 0), S = CVec.New(0, 5), W = CVec.New(-5, 0), NE = CVec.New(4, -4), SW = CVec.New(-4, 4) }
	for _, a in ipairs(marines.GetActorsByType("rifleman")) do
		a.Stance = "HoldFire"
		local key = a.Location.X == 8 and "N" or a.Location.X == 10 and "E" or a.Location.X == 12 and "S" or a.Location.X == 14 and "W" or a.Location.X == 16 and "NE" or "SW"
		if dirs[key] then a.Move(a.Location + dirs[key]) end
	end
	for _, a in ipairs(xenos.GetActorsByType("hunter")) do
		a.Stance = "HoldFire"
		local key = a.Location.X == 8 and "N" or a.Location.X == 10 and "E" or a.Location.X == 12 and "S" or a.Location.X == 14 and "W" or a.Location.X == 16 and "NE" or "SW"
		if dirs[key] then a.Move(a.Location + dirs[key]) end
	end
end
