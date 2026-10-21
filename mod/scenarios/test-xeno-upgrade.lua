-- Scenario test (see mod/test_scenarios.sh): the xeno side of the Upgrades tab, with an Evolution Tower and a Maturity Tower standing:
--   - Carapace II cannot be bought before Carapace I; the marine rifle upgrades are not on offer to xenos
--   - Carapace I, then II, Sharper Claws and Hive Speed can be bought, and nothing twice
--   - Hive Speed really makes xenos quicker: one runner walks 22 cells before the purchase, another right after it, and the second must be clearly faster.
-- Prints "TEST xeno-upgrade PASS" or "TEST xeno-upgrade FAIL".
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	xenos.Cash = 5000

	local function at(type, y)
		for _, a in ipairs(xenos.GetActorsByType(type)) do
			if a.Location.Y == y then return a end
		end
	end
	local before, after = at("runner", 6), at("runner", 12)

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
			print("TEST xeno-upgrade PASS")
		else
			print("TEST xeno-upgrade FAIL (" .. table.concat(problems, "; ") .. ")")
		end
	end

	local function waitFor(prereq, ticks, next)
		if xenos.HasPrerequisites({ prereq }) then
			next()
		elseif ticks <= 0 then
			check(false, prereq .. " never arrived")
			finish()
		else
			Trigger.AfterDelay(10, function() waitFor(prereq, ticks - 10, next) end)
		end
	end

	-- Walks the runner to x = 26 and calls back with the ticks it took.
	local function walk(runner, done)
		local function poll(ticks)
			if runner.Location.X >= 26 then
				done(ticks)
			elseif ticks > 600 then
				check(false, "a runner never arrived")
				finish()
			else
				Trigger.AfterDelay(2, function() poll(ticks + 2) end)
			end
		end
		runner.Move(CPos.New(26, runner.Location.Y))
		poll(0)
	end

	Trigger.AfterDelay(60, function()
		check(not xenos.QueueUnit("upgrade-carapace-2"), "carapace II bought before I")
		check(not xenos.QueueUnit("upgrade-rifle-t12"), "a marine upgrade was on offer to xenos")
		walk(before, function(slow)
			check(xenos.QueueUnit("upgrade-hive-speed"), "hive speed could not be queued")
			waitFor("upgrade-hive-speed", 1200, function()
				-- Hive speed alone: the second runner must be clearly quicker (12 percent, so several ticks over a walk of about 74).
				walk(after, function(fast)
					print("DBG runner ticks: before " .. slow .. ", after " .. fast)
					check(fast <= slow - 4, "the upgraded runner was not clearly faster (" .. fast .. " against " .. slow .. ")")
					check(xenos.QueueUnit("upgrade-claws"), "claws could not be queued")
					check(xenos.QueueUnit("upgrade-carapace-1"), "carapace I could not be queued")
					waitFor("upgrade-carapace-1", 2400, function()
						check(not xenos.QueueUnit("upgrade-carapace-1"), "carapace I bought twice")
						check(xenos.QueueUnit("upgrade-carapace-2"), "carapace II could not be queued after I")
						waitFor("upgrade-carapace-2", 2400, function()
							check(xenos.HasPrerequisites({ "upgrade-claws" }), "claws missing")
							check(not xenos.QueueUnit("upgrade-hive-speed"), "hive speed bought twice")
							finish()
						end)
					end)
				end)
			end)
		end)
	end)
end
