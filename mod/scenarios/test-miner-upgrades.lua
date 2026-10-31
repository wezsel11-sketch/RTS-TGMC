-- Scenario test: the economy upgrades. A miner's income over 500 ticks before and after Deep-Core Drills (18 instead of 12 per 50 ticks),
-- and both upgrades can be bought with an Armory. Prints "TEST miner-upgrades PASS" or "TEST miner-upgrades FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	marines.Cash = 5000
	local problems = {}
	local function check(ok, what)
		if not ok then
			problems[#problems + 1] = what
		end
	end

	local function finish(before, after)
		print("TEST miner-upgrades " .. (#problems == 0 and "PASS" or "FAIL") .. " (income in 500 ticks " .. before .. " before, " .. after .. " after"
			.. (#problems > 0 and "; " .. table.concat(problems, "; ") or "") .. ")")
	end

	local function waitFor(prereqs, ticks, next)
		if marines.HasPrerequisites(prereqs) then
			next()
		elseif ticks <= 0 then
			check(false, table.concat(prereqs, ", ") .. " never arrived")
			finish("-", "-")
		else
			Trigger.AfterDelay(10, function() waitFor(prereqs, ticks - 10, next) end)
		end
	end

	local cash0 = marines.Cash
	Trigger.AfterDelay(500, function()
		local before = marines.Cash - cash0
		check(marines.QueueUnit("upgrade-miner-drills"), "the drills could not be queued")
		check(marines.QueueUnit("upgrade-miner-housing"), "the housings could not be queued")
		waitFor({ "upgrade-miner-drills", "upgrade-miner-housing" }, 3000, function()
			local cash1 = marines.Cash
			Trigger.AfterDelay(500, function()
				local after = marines.Cash - cash1
				check(after * 10 >= before * 14, "the drills did not raise the income by half")
				finish(before, after)
			end)
		end)
	end)
end
