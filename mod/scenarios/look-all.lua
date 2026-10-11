-- Not a test: a map to look at (mod/smoke.sh look-all). Every unit and structure of both sides stands in rows, so the team
-- colour rings and plates, the sprites and the health bars can be checked. Most structures are hurt to different degrees
-- to show the damage overlays. It prints no TEST line, so mod/test_scenarios.sh ignores it.
WorldLoaded = function()
	local hurt = { 0.9, 0.7, 0.45, 0.2 }
	local types = { "cryo-pod", "armory", "ordnance-depot", "miner", "sentry-turret", "vendor",
		"weed-node", "resin-turret", "mini-silo", "evolution-tower", "maturity-tower", "resin-silo" }
	local n = 0
	for _, name in ipairs({ "Marines", "Xenos" }) do
		for _, a in ipairs(Player.GetPlayer(name).GetActorsByTypes(types)) do
			n = n + 1
			a.Health = math.floor(a.MaxHealth * hurt[(n % #hurt) + 1])
		end
	end
	Camera.Position = Map.CenterOfCell(CPos.New(16, 12))
end
