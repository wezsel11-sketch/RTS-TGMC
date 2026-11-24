-- Scenario test: formation movement. A runner (fast) and a crusher (slow), two cells apart, are ordered to the same far cell on the
-- same tick: they arrive within two seconds of each other and still two cells apart (the runner alone would be there long before).
-- The crusher is stuck in sticky resin (half speed), so the pace must count speed modifiers, not only the base speed.
-- Prints "TEST formation PASS" or "TEST formation FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local runner = xenos.GetActorsByType("runner")[1]
	local crusher = xenos.GetActorsByType("crusher")[1]
	local goal = CPos.New(34, 11)
	local arrived = {}
	Trigger.AfterDelay(10, function()
		crusher.GrantCondition("stuck", 3000)
		runner.OrderMove(goal)
		crusher.OrderMove(goal)
	end)
	local function watch(unit, name, ticks)
		if unit.IsIdle and ticks > 20 then
			arrived[name] = ticks
		elseif ticks < 2000 then
			Trigger.AfterDelay(5, function() watch(unit, name, ticks + 5) end)
		end
	end
	Trigger.AfterDelay(15, function() watch(runner, "runner", 0) watch(crusher, "crusher", 0) end)
	local function report(ticks)
		if arrived.runner and arrived.crusher then
			local apart = math.abs(runner.Location.Y - crusher.Location.Y)
			local gap = math.abs(arrived.runner - arrived.crusher)
			local near = math.abs(runner.Location.X - goal.X) <= 2 and math.abs(crusher.Location.X - goal.X) <= 2
			print("TEST formation " .. ((gap <= 50 and apart == 2 and near) and "PASS" or "FAIL") .. " (runner after " .. arrived.runner ..
				" ticks, crusher after " .. arrived.crusher .. ", " .. apart .. " cells apart at the end)")
		elseif ticks >= 2100 then
			print("TEST formation FAIL (not both arrived: runner " .. tostring(arrived.runner) .. ", crusher " .. tostring(arrived.crusher) .. ")")
		else
			Trigger.AfterDelay(25, function() report(ticks + 25) end)
		end
	end
	report(0)
end
