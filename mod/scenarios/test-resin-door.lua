-- Scenario test: a resin door lets the hive through and keeps marines out, and sticky resin slows a marine.
-- A runner and a rifleman each walk east along their own walled lane with a resin door in it; a second rifleman crosses a strip of
-- sticky resin while a third walks the same distance on bare ground.
-- Prints "TEST resin-door PASS" or "TEST resin-door FAIL".
WorldLoaded = function()
	local xenos, marines = Player.GetPlayer("Xenos"), Player.GetPlayer("Marines")
	local runner = xenos.GetActorsByType("runner")[1]
	local byY = {}
	for _, m in ipairs(marines.GetActorsByType("rifleman")) do
		m.Stance = "HoldFire"
		byY[m.Location.Y] = m
	end
	runner.Stance = "HoldFire"
	local blocked, slow, free = byY[14], byY[19], byY[22]
	runner.Move(CPos.New(16, 10))
	blocked.Move(CPos.New(16, 14))
	slow.Move(CPos.New(16, 19))
	free.Move(CPos.New(16, 22))
	-- The marine may walk round the short wall; what counts is that he never steps into the door's cell.
	local entered, opened = false, false
	Trigger.OnEnteredFootprint({ CPos.New(11, 14) }, function(a) if a == blocked then entered = true end end)
	Trigger.OnEnteredFootprint({ CPos.New(11, 10) }, function(a) if a == runner then opened = true end end)
	local slowed, slowX, freeX
	Trigger.AfterDelay(90, function()
		slowX, freeX = slow.Location.X, free.Location.X
		slowed = freeX - slowX >= 2
	end)
	Trigger.AfterDelay(250, function()
		local through = opened and runner.Location.X >= 14
		print("TEST resin-door " .. ((through and not entered and slowed) and "PASS" or "FAIL") .. " (runner went through its door " .. tostring(opened) .. ", x " .. runner.Location.X
			.. ", marine went through the door " .. tostring(entered) .. ", at tick 90 marine on sticky x " .. slowX .. ", on grass x " .. freeX .. ")")
	end)
end
