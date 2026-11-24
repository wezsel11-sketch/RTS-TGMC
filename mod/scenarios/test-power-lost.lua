-- Scenario test: the only building that grants support powers dies. The power tiles under the minimap were drawn once more with the dead
-- power and the game crashed (0.2.4); the harness greps for the exception. It shows only with drawing on (TGMC_FAST=0).
-- Prints "TEST power-lost PASS".
WorldLoaded = function()
	local depot = Player.GetPlayer("Marines").GetActorsByType("ordnance-depot")[1]
	Trigger.AfterDelay(60, function()
		depot.Kill()
	end)
	Trigger.AfterDelay(200, function()
		print("TEST power-lost PASS")
	end)
end
