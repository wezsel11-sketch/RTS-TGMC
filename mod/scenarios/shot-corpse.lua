-- Screenshot scene: a marine and a hunter are killed, and the picture is taken some seconds later to show the bodies still lying there.
WorldLoaded = function()
	Trigger.AfterDelay(5, function()
		for _, a in ipairs(Player.GetPlayer("Marines").GetActorsByType("rifleman")) do
			a.Kill()
		end
		for _, a in ipairs(Player.GetPlayer("Xenos").GetActorsByType("hunter")) do
			a.Kill()
		end
	end)
end
