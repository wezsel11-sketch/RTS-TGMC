-- Scenario test: in a mixed group only the units that have an ability in a slot use it: the squad leader smokes, the riflemen refuse.
-- Prints "TEST card-mixed PASS" or "TEST card-mixed FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	Trigger.AfterDelay(10, function()
		local leader = marines.GetActorsByType("squad_leader")[1].UseAbility(1)
		local riflemen = 0
		Utils.Do(marines.GetActorsByType("rifleman"), function(a)
			-- A unit with no ability at all has no UseAbility: that counts as refusing.
			local ok, used = pcall(function() return a.UseAbility(1) end)
			if ok and used then riflemen = riflemen + 1 end
		end)
		print("TEST card-mixed " .. ((leader and riflemen == 0) and "PASS" or "FAIL") .. " (leader=" .. tostring(leader) .. ", riflemen=" .. riflemen .. ")")
	end)
end
