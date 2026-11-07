-- Scenario test: bot personalities (ai.yaml). The marine bot starts with eight riflemen beside its cryo pod and no money; the xeno
-- silo stands across the map. The Rusher forms a small squad and sends it out; the Turtle waits for a squad it can never fill. At
-- tick 1500 it counts riflemen more than 15 cells from the pod (the scout may be one of them). A case script sets Personality:
-- "rusher" expects 3 or more out, "turtle" at most 1.
-- Prints "TEST ai-personality-<personality> PASS|FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local pod = marines.GetActorsByType("cryo-pod")[1]
	Trigger.AfterDelay(1500, function()
		local out = 0
		for _, a in ipairs(marines.GetActorsByType("rifleman")) do
			if math.abs(a.Location.X - pod.Location.X) + math.abs(a.Location.Y - pod.Location.Y) > 15 then out = out + 1 end
		end
		local ok = (Personality == "rusher" and out >= 3) or (Personality == "turtle" and out <= 1)
		print("TEST ai-personality-" .. Personality .. " " .. (ok and "PASS" or "FAIL") .. " (" .. out .. " riflemen out at tick 1500)")
	end)
end
