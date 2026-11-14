-- Scenario test: the landing intro (FactionStart with the lobby's Landing intro option, on by default). The marines'
-- building stands from the start; their three units ride the Alamo down, walk out once it has landed, and the ship
-- leaves. Prints "TEST landing-intro PASS" or "TEST landing-intro FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local function units()
		return #marines.GetActorsByType("rifleman") + #marines.GetActorsByType("medic")
	end

	local early, podEarly, shipEarly
	Trigger.AfterDelay(40, function()
		early = units()
		podEarly = #marines.GetActorsByType("cryo-pod")
		shipEarly = #marines.GetActorsByType("alamo-drop")
	end)

	Trigger.AfterDelay(400, function()
		local late = units()
		local shipLate = #marines.GetActorsByType("alamo-drop")
		local ok = early == 0 and podEarly == 1 and shipEarly == 1 and late == 3 and shipLate == 0
		print("TEST landing-intro " .. (ok and "PASS" or "FAIL") .. " (tick 40: units " .. early .. ", pod " .. podEarly
			.. ", ship " .. shipEarly .. "; tick 400: units " .. late .. ", ship " .. shipLate .. ")")
	end)
end
