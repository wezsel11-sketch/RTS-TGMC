-- Screenshot scene: the camera looks at the ground where the howitzer shell lands. The xenos stand still.
WorldLoaded = function()
	Camera.Position = Map.CenterOfCell(CPos.New(24, 12))
	for _, a in ipairs(Player.GetPlayer("Xenos").GetActorsByType("crusher")) do
		a.Stance = "HoldFire"
	end
	for _, a in ipairs(Player.GetPlayer("Marines").GetActorsByType("rifleman")) do
		a.Stance = "HoldFire"
	end
end
