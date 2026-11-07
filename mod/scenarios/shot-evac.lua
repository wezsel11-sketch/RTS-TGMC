-- Not a test: the Alamo lands at once on the Evac map and the marines run for it, to see the ship and its open doors.
ConfigOverride = function(config)
	config.waves = { { delay = 20, pay = 0, units = { { "runner", 4 } } } }
	config.landDelay = 30
	config.shuttleWait = 5000
	config.assaultInterval = 100000
end

AfterStart = function()
	Camera.Position = Map.CenterOfCell(CPos.New(42, 24))
	Trigger.AfterDelay(60, function()
		for _, a in ipairs(Player.GetPlayer("Marines").GetActorsByTypes({ "rifleman", "medic", "engineer" })) do
			a.Move(CPos.New(44, 31))
		end
	end)
end
