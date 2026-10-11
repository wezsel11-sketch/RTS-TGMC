-- Scenario test (see mod/test_scenarios.sh): runs the real wave script with two tiny waves near the marines and checks
-- that the xenos spawn, attack, and that clearing them wins the game for the marines.
-- Prints "TEST waves PASS" or "TEST waves FAIL". The wave script calls these two hooks from its WorldLoaded.
local reported = false

ConfigOverride = function(config)
	config.spawnCells = { CPos.New(15, 10), CPos.New(15, 12) }
	config.waves =
	{
		{ delay = 50, units = { { "runner", 2 } } },
		{ delay = 50, units = { { "runner", 2 }, { "hunter", 1 } } },
	}
end

AfterStart = function()
	Trigger.OnPlayerWon(Marines, function()
		if not reported then
			reported = true
			print("TEST waves PASS (marines won after " .. WavesSent .. " waves)")
		end
	end)

	Trigger.AfterDelay(1500, function()
		if not reported then
			reported = true
			print("TEST waves FAIL (waves sent: " .. WavesSent .. ", xenos alive: " .. #Xenos.GetActorsByTypes(XenoTypes) .. ")")
		end
	end)
end
