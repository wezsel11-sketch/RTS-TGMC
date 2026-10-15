-- Not a test: a marine walks into a door, to see it open.
WorldLoaded = function()
	local rifleman = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	Trigger.AfterDelay(10, function()
		rifleman.Move(CPos.New(18, 11))
	end)
	Trigger.AfterDelay(500, function()
		print("TEST door " .. (rifleman.Location.X >= 17 and "PASS" or "FAIL") .. " (marine at x " .. rifleman.Location.X .. ")")
	end)
end
