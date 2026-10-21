-- Scenario test: a facehugger beside a rifleman latches on (the rifleman goes down); beside a synthetic it cannot.
-- Prints "TEST synth-infest PASS" or "TEST synth-infest FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local man = marines.GetActorsByType("rifleman")[1]
	local synth = marines.GetActorsByType("synth")[1]
	local hugs = xenos.GetActorsByType("facehugger")
	local function at(y)
		for _, a in ipairs(hugs) do
			if a.Location.Y == y then return a end
		end
	end
	local hugMan, hugSynth = at(8), at(20)
	man.Stance = "HoldFire"
	synth.Stance = "HoldFire"
	hugMan.Attack(man, true, false)
	hugSynth.Attack(synth, true, false)

	-- A facehugger that latches on is used up (dead); one that cannot is still there and the synth is untouched.
	Trigger.AfterDelay(250, function()
		local problems = {}
		if not hugMan.IsDead then problems[#problems + 1] = "the control facehugger did not latch onto the rifleman" end
		if hugSynth.IsDead then problems[#problems + 1] = "a facehugger latched onto the synth" end
		if synth.Health < synth.MaxHealth then problems[#problems + 1] = "the synth was hurt" end
		if not reported then
			reported = true
			if #problems == 0 then
				print("TEST synth-infest PASS")
			else
				print("TEST synth-infest FAIL (" .. table.concat(problems, "; ") .. ")")
			end
		end
	end)
end
