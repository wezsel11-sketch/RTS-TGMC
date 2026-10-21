-- Scenario test: a full load of buckshot throws a small xeno back a few cells; a big one stays put. Two rows, 14 cells apart:
--   y 8:  a skirmisher (shotgun) 2 cells from a runner  -> the runner must end up at least 2 cells further away, alive or dead
--   y 22: a skirmisher 2 cells from a warrior (not a small xeno) -> the warrior must not be thrown
-- Prints "TEST shotgun-knockback PASS" or "TEST shotgun-knockback FAIL" after 200 ticks.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local function at(player, type, y)
		for _, a in ipairs(player.GetActorsByType(type)) do
			if a.Location.Y == y then return a end
		end
	end
	local gunA, runner = at(marines, "skirmisher", 8), at(xenos, "runner", 8)
	local gunB, warrior = at(marines, "skirmisher", 22), at(xenos, "warrior", 22)
	for _, a in ipairs({ gunA, runner, gunB, warrior }) do
		a.Stance = "HoldFire"
	end
	local runnerStart, warriorStart = runner.Location.X, warrior.Location.X
	local runnerLanded, warriorMoved = runnerStart, warriorStart

	Trigger.AfterDelay(5, function()
		gunA.Attack(runner, false, false)
		gunB.Attack(warrior, false, false)
	end)

	-- The runner may die on the way; keep the furthest x it was seen at.
	local function watch(ticks)
		if not runner.IsDead then
			runnerLanded = math.max(runnerLanded, runner.Location.X)
		end
		if not warrior.IsDead then
			warriorMoved = math.max(warriorMoved, warrior.Location.X)
		end
		if ticks > 0 then
			Trigger.AfterDelay(2, function() watch(ticks - 2) end)
		end
	end
	watch(200)

	Trigger.AfterDelay(200, function()
		local thrown = runnerLanded - runnerStart >= 2
		local steady = warriorMoved - warriorStart < 2
		print("DBG runner x " .. runnerStart .. " to " .. runnerLanded .. ", warrior x " .. warriorStart .. " to " .. warriorMoved)
		print("TEST shotgun-knockback " .. ((thrown and steady) and "PASS" or "FAIL") .. " (runner thrown " .. tostring(thrown) .. ", warrior steady " .. tostring(steady) .. ")")
	end)
end
