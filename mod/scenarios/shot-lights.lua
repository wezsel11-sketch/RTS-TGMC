-- Screenshot scene: the camera looks at a fire, a pool of acid and a gas cloud, to see their glow.
WorldLoaded = function()
	Camera.Position = Map.CenterOfCell(CPos.New(20, 13))
	for _, a in ipairs(Player.GetPlayer("Xenos").GetActorsByType("hunter")) do
		a.Stance = "HoldFire"
	end
	for _, a in ipairs(Player.GetPlayer("Marines").GetActorsByType("rifleman")) do
		a.Stance = "HoldFire"
	end
end
