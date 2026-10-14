-- Scenario test (see mod/test_scenarios.sh): the Queen's screech stuns marines within range, so one next to her stands still while
-- one far away walks on. Prints "TEST screech PASS" or "TEST screech FAIL".
WorldLoaded = function()
	local marines, xenos = Player.GetPlayer("Marines"), Player.GetPlayer("Xenos")
	local queen = xenos.GetActorsByType("queen")[1]
	local near = marines.GetActorsByType("rifleman")[1]
	local far = marines.GetActorsByType("rifleman")[2]
	local nearStart, farStart = near.Location, far.Location

	Trigger.AfterDelay(2, function()
		near.Move(CPos.New(near.Location.X, near.Location.Y + 9))
		far.Move(CPos.New(far.Location.X, far.Location.Y + 9))
	end)
	Trigger.AfterDelay(4, function()
		queen.Screech()
	end)
	Trigger.AfterDelay(70, function()
		local movedNear = math.abs(near.Location.Y - nearStart.Y)
		local movedFar = math.abs(far.Location.Y - farStart.Y)
		if movedNear <= 1 and movedFar >= 3 then
			print("TEST screech PASS (near moved " .. movedNear .. ", far moved " .. movedFar .. ")")
		else
			print("TEST screech FAIL (near moved " .. movedNear .. ", far moved " .. movedFar .. ")")
		end
	end)
end
