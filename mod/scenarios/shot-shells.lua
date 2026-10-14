-- Screenshot scene: the camera looks at the ground where the mortar and the howitzer shells land. The xenos stand still.
WorldLoaded = function()
	Camera.Position = Map.CenterOfCell(CPos.New(18, 15))
	for _, a in ipairs(Player.GetPlayer("Xenos").GetActorsByType("crusher")) do
		a.Stance = "HoldFire"
	end
	for _, a in ipairs(Player.GetPlayer("Marines").GetActorsByType("rifleman")) do
		a.Stance = "HoldFire"
	end
end
