-- Scenario test: the Night Raid waves spawn from the east edge and march. Prints "TEST raid PASS" or "TEST raid FAIL".
AfterStart = function()
	Trigger.AfterDelay(1500, function()
		local xenos = Player.GetPlayer("Xenos")
		local n = #xenos.GetActorsByTypes({ "runner", "hunter", "spitter", "drone" })
		local spitters = #xenos.GetActorsByType("spitter")
		print("TEST raid " .. ((n >= 6 and WavesSent >= 2) and "PASS" or "FAIL") .. " (" .. n .. " xenos alive, " .. spitters .. " spitters, " .. WavesSent .. " waves sent)")
	end)
end
