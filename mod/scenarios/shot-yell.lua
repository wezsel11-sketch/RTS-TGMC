-- Not a test: the squad leader yells MOVE! among his squad, for the yell screenshot (shot-yell map).
WorldLoaded = function()
	local leader = Player.GetPlayer("Marines").GetActorsByType("squad_leader")[1]
	-- Something moves the camera back at the start: keep putting it on the action, as shot_map.py does.
	local at = leader.CenterPosition
	local function look()
		Camera.Position = at
		Trigger.AfterDelay(3, look)
	end
	look()
	Trigger.AfterDelay(66, function() leader.UseAbility(4) end)
end
