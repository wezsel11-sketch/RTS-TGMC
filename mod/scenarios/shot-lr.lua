-- Screenshot scene: marines shoot at hunters to their west and east, so the picture shows which way each one faces. Run by shot-lr.
WorldLoaded = function()
	for _, h in ipairs(Player.GetPlayer("Xenos").GetActorsByType("hunter")) do
		h.Stance = "HoldFire"
	end
end
