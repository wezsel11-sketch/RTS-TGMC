-- Not a test: the castes added from TGMC side by side, to look at them.
WorldLoaded = function()
	Camera.Position = Map.CenterOfCell(CPos.New(16, 9))
	for _, a in ipairs(Player.GetPlayer("Xenos").GetActors()) do
		if a.HasProperty("Stance") then a.Stance = "HoldFire" end
	end
end
