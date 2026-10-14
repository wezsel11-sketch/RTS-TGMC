-- Not a test: wounded marines for the "To medic" button screenshot (shot-medic map).
WorldLoaded = function()
	for _, a in ipairs(Player.GetPlayer("Marines").GetActorsByType("rifleman")) do
		a.Health = 40
	end
end
