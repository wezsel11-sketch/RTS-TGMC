-- Scenario test: a door (mapdoor-0) in a line of rock opens for a marine, who walks through it to the other side.
-- Prints "TEST door PASS" or "TEST door FAIL".
WorldLoaded = function()
	local rifleman = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	Trigger.AfterDelay(10, function()
		rifleman.Move(CPos.New(18, 11))
	end)
	Trigger.AfterDelay(500, function()
		print("TEST door " .. (rifleman.Location.X >= 17 and "PASS" or "FAIL") .. " (marine at x " .. rifleman.Location.X .. ")")
	end)
end
