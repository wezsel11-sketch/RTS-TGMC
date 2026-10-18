-- Scenario test (see mod/test_scenarios.sh): with no friendly return point, Retreat is refused and the rifleman does not move.
-- Prints "TEST retreat-none PASS" or "TEST retreat-none FAIL".
local done = false

WorldLoaded = function()
	local rifleman = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	local startX, startY = rifleman.Location.X, rifleman.Location.Y
	local accepted = rifleman.Retreat()

	local function poll(ticks)
		if done then
			return
		end
		local moved = rifleman.Location.X ~= startX or rifleman.Location.Y ~= startY
		if moved or accepted then
			done = true
			print("TEST retreat-none FAIL (accepted=" .. tostring(accepted) .. ", moved=" .. tostring(moved) .. ")")
		elseif ticks >= 100 then
			done = true
			print("TEST retreat-none PASS (refused, did not move)")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
