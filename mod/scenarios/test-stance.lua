-- Scenario test (see mod/test_scenarios.sh): a Hold Fire rifleman must not shoot a Runner in range, an Attack Anything rifleman must.
-- Prints "TEST stance PASS" or "TEST stance FAIL".
local done = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines").GetActorsByType("rifleman")
	local runners = Player.GetPlayer("Xenos").GetActorsByType("runner")
	local hold, aggressive, holdRunner, aggressiveRunner
	for _, r in ipairs(marines) do
		if r.Location.Y == 10 then hold = r else aggressive = r end
	end
	for _, r in ipairs(runners) do
		if r.Location.Y == 10 then holdRunner = r else aggressiveRunner = r end
	end
	hold.Stance = "HoldFire"
	aggressive.Stance = "AttackAnything"
	local holdMax, aggressiveMax = holdRunner.MaxHealth, aggressiveRunner.MaxHealth

	local function poll(ticks)
		if done then
			return
		end
		local aggressiveHurt = aggressiveRunner.IsDead or aggressiveRunner.Health < aggressiveMax
		local holdHurt = holdRunner.IsDead or holdRunner.Health < holdMax
		if aggressiveHurt and not holdHurt and ticks >= 150 then
			done = true
			print("TEST stance PASS (attack-anything hit, hold-fire did not, by tick " .. ticks .. ")")
		elseif holdHurt then
			done = true
			print("TEST stance FAIL (hold-fire rifleman shot its runner)")
		elseif ticks >= 300 then
			done = true
			print("TEST stance FAIL (attack-anything hurt=" .. tostring(aggressiveHurt) .. ", hold-fire hurt=" .. tostring(holdHurt) .. ")")
		else
			Trigger.AfterDelay(5, function() poll(ticks + 5) end)
		end
	end
	Trigger.AfterDelay(5, function() poll(5) end)
end
