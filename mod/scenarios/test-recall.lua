-- Scenario test: the town bell (Recall). Two riflemen and an engineer stand at a miner far from the base, a third rifleman stands
-- elsewhere. Ringing the bell at the miner sends the three near it back toward the cryo pod; the one outside the radius stays.
-- Prints "TEST recall PASS" or "TEST recall FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local pod = marines.GetActorsByType("cryo-pod")[1]
	local near, far = {}, nil
	for _, t in ipairs({ "rifleman", "engineer" }) do
		for _, a in ipairs(marines.GetActorsByType(t)) do
			if a.Location.Y < 10 then far = a else near[#near + 1] = a end
		end
	end
	local function dist(a) return math.abs(a.Location.X - pod.Location.X) + math.abs(a.Location.Y - pod.Location.Y) end
	local before = {}
	for i, a in ipairs(near) do before[i] = dist(a) end
	local farStart = far.Location
	Trigger.AfterDelay(10, function() pod.CallRecall(CPos.New(40, 20)) end)
	Trigger.AfterDelay(300, function()
		local ok, parts = true, {}
		for i, a in ipairs(near) do
			parts[#parts + 1] = a.Type .. " " .. before[i] .. "->" .. dist(a)
			if dist(a) > before[i] - 10 then ok = false end
		end
		local stayed = far.Location == farStart
		print("TEST recall " .. ((ok and stayed) and "PASS" or "FAIL") .. " (" .. table.concat(parts, ", ") .. ", far rifleman stayed " .. tostring(stayed) .. ")")
	end)
end
