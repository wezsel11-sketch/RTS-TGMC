-- Screenshot scene: two marines and a hunter are blown apart, and their body parts fly out. A medic stays alive so that the ground is in sight.
WorldLoaded = function()
	Camera.Position = Map.CenterOfCell(CPos.New(16, 13))
	Player.GetPlayer("Marines").GetActorsByType("medic")[1].Stance = "HoldFire"
	Trigger.AfterDelay(10, function()
		for _, a in ipairs(Player.GetPlayer("Marines").GetActorsByType("rifleman")) do
			a.Kill("ExplosionDeath")
		end
		for _, a in ipairs(Player.GetPlayer("Xenos").GetActorsByType("hunter")) do
			a.Kill("ExplosionDeath")
		end
	end)
end
