-- Scenario test: a xeno has to pry a colony door open (PryTicks on ^MapDoor). A runner walks through a closed door; the map's
-- Pry variable (mode-door-pry-*.lua) says whether this map has the pry on (it should take PryTicks longer) or off. It is told
-- once: the door sends it on when it opens.
-- Prints "TEST door-pry-on PASS" or "TEST door-pry-off PASS", or FAIL.
WorldLoaded = function()
	local runner = Player.GetPlayer("Xenos").GetActorsByType("runner")[1]
	local name = "door-pry-" .. (Pry and "on" or "off")
	local through = nil
	Trigger.AfterDelay(10, function() runner.Move(CPos.New(18, 11)) end)
	local function look(ticks)
		if runner.Location.X >= 15 then
			through = ticks
		end
		if through or ticks > 600 then
			local ok = through ~= nil and ((Pry and through >= PryFrom) or (not Pry and through < PryFrom - 30))
			print("TEST " .. name .. " " .. (ok and "PASS" or "FAIL") .. " (through the door at " .. tostring(through) .. ", pry cut-off " .. PryFrom .. ")")
			return
		end
		Trigger.AfterDelay(1, function() look(ticks + 1) end)
	end
	look(0)
end
