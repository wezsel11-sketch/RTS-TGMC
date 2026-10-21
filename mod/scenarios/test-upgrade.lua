-- Scenario test (see mod/test_scenarios.sh): the Upgrades tab and the rifle ladder. With an Armory standing:
--   - the M412 rifles cannot be bought before the T-12 rifles (they need them)
--   - the T-12 rifles can be bought, and when they finish the player holds the prerequisite that switches the rifleman's gun
--   - then the M412 rifles can be bought the same way, and nothing can be bought twice
--   - the gun really changes: two riflemen on hold fire are ordered to shoot a runner each (a runner is point-sized; a building would count by its edge), one 8.5 cells away (out of the carbine's range of 8,
--     in the T-12's 9) and one 9.9 cells away (out of the T-12's range, in the M412's 10). Neither runner may be touched until its upgrade is bought.
-- Prints "TEST upgrade PASS" or "TEST upgrade FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	marines.Cash = 3000

	local function at(player, type, x)
		for _, a in ipairs(player.GetActorsByType(type)) do
			if a.Location.X == x then return a end
		end
	end
	local near, nearRunner = at(marines, "rifleman", 8), at(xenos, "runner", 14)
	local far, farRunner = at(marines, "rifleman", 4), at(xenos, "runner", 11)
	near.Stance = "HoldFire"
	nearRunner.Stance = "HoldFire"
	farRunner.Stance = "HoldFire"
	far.Stance = "HoldFire"
	local nearMax, farMax = nearRunner.MaxHealth, farRunner.MaxHealth

	local problems = {}
	local function check(ok, what)
		if not ok then
			problems[#problems + 1] = what
		end
	end

	local function finish()
		if reported then
			return
		end
		reported = true
		if #problems == 0 then
			print("TEST upgrade PASS")
		else
			print("TEST upgrade FAIL (" .. table.concat(problems, "; ") .. ")")
		end
	end

	local function waitFor(prereq, ticks, next)
		if marines.HasPrerequisites({ prereq }) then
			next()
		elseif ticks <= 0 then
			check(false, prereq .. " never arrived")
			finish()
		else
			Trigger.AfterDelay(10, function() waitFor(prereq, ticks - 10, next) end)
		end
	end

	-- Orders the rifleman to shoot (without walking closer) and reports after a while whether the runner is hurt.
	local function volley(man, target, max, then_)
		man.Attack(target, false, false)
		Trigger.AfterDelay(150, function() then_(target.IsDead or target.Health < max) end)
	end

	-- The queue wakes up on the first tick, so start a moment after the world loads.
	Trigger.AfterDelay(60, function()
		check(not marines.QueueUnit("upgrade-rifle-m412"), "m412 bought before t12")
		check(not marines.HasPrerequisites({ "upgrade-rifle-t12" }), "t12 held at the start")
		volley(near, nearRunner, nearMax, function(hurt)
			check(not hurt, "the carbine hit a runner 8.5 cells away")
			check(marines.QueueUnit("upgrade-rifle-t12"), "t12 could not be queued")
			waitFor("upgrade-rifle-t12", 1200, function()
				check(not marines.QueueUnit("upgrade-rifle-t12"), "t12 bought twice")
				volley(near, nearRunner, nearMax, function(nearHurt)
					check(nearHurt, "the T-12 did not reach a runner 8.5 cells away")
					volley(far, farRunner, farMax, function(farHurt)
						check(not farHurt, "the T-12 hit a runner 9.9 cells away")
						check(marines.QueueUnit("upgrade-rifle-m412"), "m412 could not be queued after t12")
						waitFor("upgrade-rifle-m412", 1500, function()
							volley(far, farRunner, farMax, function(farHurtNow)
								check(farHurtNow, "the M412 did not reach a runner 9.9 cells away")
								finish()
							end)
						end)
					end)
				end)
			end)
		end)
	end)
end
