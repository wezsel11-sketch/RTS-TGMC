-- Scenario test (see mod/test_scenarios.sh): a marine that dies leaves a corpse, and the corpse is removed again after a
-- while. A second marine stays alive far away so the game does not end. Prints "TEST death PASS" or "TEST death FAIL".
local function CorpsesNear(cell)
	local found = {}
	for _, a in ipairs(Map.ActorsInBox(Map.CenterOfCell(cell - CVec.New(2, 2)), Map.CenterOfCell(cell + CVec.New(2, 2)))) do
		if a.Type == "rifleman-corpse" then
			table.insert(found, a)
		end
	end
	return #found
end

WorldLoaded = function()
	local victim = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	local cell = victim.Location
	Trigger.AfterDelay(10, function()
		victim.Kill()
	end)
	Trigger.AfterDelay(60, function()
		local made = CorpsesNear(cell)
		Trigger.AfterDelay(900, function()
			local left = CorpsesNear(cell)
			if made >= 1 and left == 0 then
				print("TEST death PASS (" .. made .. " corpse after the kill, none after it expired)")
			else
				print("TEST death FAIL (corpses after the kill: " .. made .. ", after expiry: " .. left .. ")")
			end
		end)
	end)
end
