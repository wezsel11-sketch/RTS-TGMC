-- Not a test: a mech walks into a few hunters and fights them, for the mech effects screenshot (shot-mech-fx map): dust under its feet,
-- smoke at its guns, sparks where it is hit.
WorldLoaded = function()
	local mech = Player.GetPlayer("Marines").GetActorsByType("mech")[1]
	local at = Map.CenterOfCell(CPos.New(14, 12))
	local function look()
		Camera.Position = at
		Trigger.AfterDelay(3, look)
	end
	look()
	mech.AttackMove(CPos.New(18, 12))
end
