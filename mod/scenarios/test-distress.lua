-- Scenario test: TGMC's Distress Signal objective. Riflemen stand at the three disk terminals until they are decoded; a rifleman who
-- waited at the nuke all along can only arm it after that; armed, it counts down and goes off, and nothing of the hive is left.
-- Prints "TEST distress PASS" or "TEST distress FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local early = nil

	for _, a in ipairs(marines.GetActors()) do
		a.Stance = "HoldFire"
	end

	-- Before the terminals are done (500 ticks of holding) the nuke must still be neutral.
	Trigger.AfterDelay(450, function()
		early = #marines.GetActorsByType("nuke")
	end)

	local function look(ticks)
		local terminals = #marines.GetActorsByType("disk-terminal")
		local nuke = #marines.GetActorsByType("nuke")
		local hive = #xenos.GetActorsByType("resin-silo") + #xenos.GetActorsByType("runner")
		if hive == 0 then
			local ok = early == 0 and terminals == 3
			print("TEST distress " .. (ok and "PASS" or "FAIL") .. " (terminals " .. terminals .. ", nuke owned " .. nuke ..
				", nuke owned at 450: " .. tostring(early) .. ", hive gone at " .. ticks .. ")")
		elseif ticks > 3500 then
			print("TEST distress FAIL (timed out: terminals " .. terminals .. ", nuke owned " .. nuke .. ", hive " .. hive .. ")")
		else
			Trigger.AfterDelay(25, function() look(ticks + 25) end)
		end
	end
	look(0)
end
