-- Scenario test: the Crash objective (CrashTimer, cut to 600 ticks for the test). Nobody touches the nuke, the clock runs out,
-- and the marines lose everything. Prints "TEST crash PASS" or "TEST crash FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	for _, a in ipairs(marines.GetActors()) do
		a.Stance = "HoldFire"
	end
	Trigger.AfterDelay(500, function()
		local before = #marines.GetActorsByType("rifleman")
		Trigger.AfterDelay(300, function()
			-- They fall as downed marines (this test map has no conquest rules to end the match), so only standing ones count.
			local after = #marines.GetActorsByType("rifleman")
			print("TEST crash " .. ((before == 2 and after == 0) and "PASS" or "FAIL") .. " (riflemen at 500: " .. before .. ", left at 800: " .. after .. ")")
		end)
	end)
end
