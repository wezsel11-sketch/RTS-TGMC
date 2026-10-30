-- Not a test: the shot-ranks map. Gives the riflemen one, two and three ranks and the squad leader part of the way to Elite,
-- and keeps the camera on them for the screenshot.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	for i, r in ipairs(marines.GetActorsByType("rifleman")) do
		r.GiveLevels(i, true)
	end
	local leader = marines.GetActorsByType("squad_leader")[1]
	leader.GiveLevels(2, true)
	leader.GiveExperience(math.floor(leader.Experience / 3), true)
	local at = leader.CenterPosition
	local function look()
		Camera.Position = at
		Trigger.AfterDelay(3, look)
	end
	look()
end
