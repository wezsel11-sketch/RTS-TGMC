-- Scenario test (see mod/test_scenarios.sh): xenos move faster near a Weed Node. Two Runners get the same order, to run
-- twenty cells east; one starts beside a Weed Node, the other far from it. After 60 ticks the one on the weeds has covered
-- at least 15% more ground (the weeds give 25% more speed while it stays on them).
-- Prints "TEST weeds PASS" or "TEST weeds FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local on, off
	for _, a in ipairs(xenos.GetActorsByType("runner")) do
		if a.Location.Y == 5 then
			on = a
		else
			off = a
		end
	end
	local x0 = on.Location.X
	on.Move(CPos.New(x0 + 20, 5))
	off.Move(CPos.New(x0 + 20, 20))
	Trigger.AfterDelay(60, function()
		local a, b = on.Location.X - x0, off.Location.X - x0
		print("TEST weeds " .. ((a >= 1 and a * 100 >= b * 115) and "PASS" or "FAIL") .. " (the Runner on the weeds covered " .. a .. " cells, the other " .. b .. ")")
	end)
end
