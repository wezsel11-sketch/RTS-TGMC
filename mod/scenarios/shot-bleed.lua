-- Screenshot scene: a crusher claws a marine while another marine shoots it: red and green blood on the floor.
WorldLoaded = function()
	Camera.Position = Map.CenterOfCell(CPos.New(16, 12))
	local marines = Player.GetPlayer("Marines").GetActorsByType("rifleman")
	marines[1].Stance = "HoldFire"
	local crusher = Player.GetPlayer("Xenos").GetActorsByType("crusher")[1]
	Trigger.AfterDelay(15, function() crusher.Attack(marines[1], true, true) end)
end
