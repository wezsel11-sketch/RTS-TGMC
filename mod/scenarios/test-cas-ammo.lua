-- Scenario test: every CAS ammo type of the ordnance depot (bombs, 30mm, mini-rockets, flare, Widowmaker, laser, napalm, Fatty, MOAB) can
-- be called in on its own hunter and hurts or kills it (the flare only has to run). Prints "TEST cas-ammo PASS" or "TEST cas-ammo FAIL".
local variants = { "cas", "gun", "minirocket", "flare", "widowmaker", "laser", "napalm", "fatty", "moab" }

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local depot = marines.GetActorsByType("ordnance-depot")[1]
	local hunters = xenos.GetActorsByType("hunter")
	table.sort(hunters, function(a, b) return a.Location.X < b.Location.X end)
	local spots = {}
	for i, h in ipairs(hunters) do
		h.Stance = "HoldFire"
		spots[i] = h.Location
	end

	local failures = {}
	local done = 0
	for i, variant in ipairs(variants) do
		local hunter = hunters[i]
		local before
		Trigger.AfterDelay(20 + (i - 1) * 380, function()
			before = hunter.IsDead and 0 or hunter.Health
			local alive = {}
			for _, h in ipairs(hunters) do alive[#alive + 1] = h.IsDead and "x" or "o" end
			print("STAT " .. variant .. " alive " .. table.concat(alive))
			local ok, err = pcall(function() depot.ActivateCondorStrike(spots[i], variant) end)
			if not ok then
				table.insert(failures, variant .. " (" .. tostring(err) .. ")")
			end
		end)
		Trigger.AfterDelay(20 + (i - 1) * 380 + 360, function()
			local hurt = hunter.IsDead or hunter.Health < before
			if variant ~= "flare" and not hurt then
				table.insert(failures, variant .. " (no damage)")
			end
			done = done + 1
			if done == #variants then
				print("TEST cas-ammo " .. (#failures == 0 and "PASS" or "FAIL") .. " (" .. #variants .. " ammo types" .. (#failures > 0 and ", failed: " .. table.concat(failures, "; ") or "") .. ")")
			end
		end)
	end
end
