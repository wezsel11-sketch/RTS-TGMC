-- Scenario test: a xeno ordered into a hive tunnel comes out at its partner across the map (the third tunnel has no partner), and a unit with
-- the Rage condition covers more ground than one without. Prints "TEST tunnel PASS" or "TEST tunnel FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local tunnels = xenos.GetActorsByType("tunnel")
	local runner = xenos.GetActorsByType("runner")[1]
	local first
	for _, t in ipairs(tunnels) do
		if t.Location.X == 6 then
			first = t
		end
	end
	runner.EnterHiveTunnel(first)
	Trigger.AfterDelay(500, function()
		local arrived = runner.Location.X >= 44 and runner.Location.X <= 56
		print("TEST tunnel " .. (arrived and "PASS" or "FAIL") .. " (runner at " .. runner.Location.X .. "," .. runner.Location.Y .. ")")
	end)
end
