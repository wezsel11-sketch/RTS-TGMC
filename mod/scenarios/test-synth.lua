-- Scenario test (see mod/test_scenarios.sh): the synthetic does a medic's, an engineer's and a fighter's work.
--   - a wounded rifleman beside it gets healed
--   - a damaged armory beside it gets repaired
--   - a runner that comes next to it gets hurt by its baton
--   - it cannot be bought without a Medbay, and two at most can be bought
-- Prints "TEST synth PASS" or "TEST synth FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	marines.Cash = 3000

	local synth = marines.GetActorsByType("synth")[1]
	local rifleman = marines.GetActorsByType("rifleman")[1]
	local armory = marines.GetActorsByType("armory")[1]
	local runner = xenos.GetActorsByType("runner")[1]
	-- Only the synth fights: the rifleman and the runner hold fire, so a hurt runner can only be the synth's doing.
	rifleman.Stance = "HoldFire"
	runner.Stance = "HoldFire"
	rifleman.Health = rifleman.MaxHealth / 3
	armory.Health = armory.MaxHealth / 3
	local manHealth, armoryHealth, runnerMax = rifleman.Health, armory.Health, runner.MaxHealth

	local problems = {}
	local function check(ok, what)
		if not ok then
			problems[#problems + 1] = what
		end
	end

	Trigger.AfterDelay(60, function()
		check(not marines.QueueUnit("synth"), "a synth could be bought without a medbay")
	end)

	Trigger.AfterDelay(400, function()
		check(rifleman.Health > manHealth, "the synth did not heal the rifleman")
		check(armory.Health > armoryHealth, "the synth did not repair the armory")
		check(runner.IsDead or runner.Health < runnerMax, "the synth did not hit the runner next to it")
		if not reported then
			reported = true
			if #problems == 0 then
				print("TEST synth PASS")
			else
				print("TEST synth FAIL (" .. table.concat(problems, "; ") .. ")")
			end
		end
	end)
end
