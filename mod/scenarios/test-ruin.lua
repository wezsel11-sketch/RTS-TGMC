-- Scenario test (see mod/test_scenarios.sh): a destroyed structure leaves rubble, and the rubble goes away again.
-- Prints "TEST ruin PASS" or "TEST ruin FAIL".
local function RubbleNear(cell)
	local n = 0
	for _, a in ipairs(Map.ActorsInBox(Map.CenterOfCell(cell - CVec.New(3, 3)), Map.CenterOfCell(cell + CVec.New(3, 3)))) do
		if string.sub(a.Type, 1, 6) == "rubble" then
			n = n + 1
		end
	end
	return n
end

WorldLoaded = function()
	local victim = Player.GetPlayer("Marines").GetActorsByType("armory")[1]
	local cell = victim.Location
	Trigger.AfterDelay(10, function() victim.Kill() end)
	Trigger.AfterDelay(60, function()
		local made = RubbleNear(cell)
		Trigger.AfterDelay(1600, function()
			local left = RubbleNear(cell)
			if made >= 1 and left == 0 then
				print("TEST ruin PASS (rubble after the kill: " .. made .. ", after it faded: " .. left .. ")")
			else
				print("TEST ruin FAIL (rubble after the kill: " .. made .. ", after it faded: " .. left .. ")")
			end
		end)
	end)
end
