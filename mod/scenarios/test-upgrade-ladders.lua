-- Scenario test (see mod/test_scenarios.sh): the one-step weapon ladders (SMG, shotgun, machine gun, rocket). With an Armory, an Ordnance Depot and a Workshop standing:
--   - all four can be bought, once each, and the player then holds each prerequisite
--   - the gun really changes: a machine gunner on hold fire is ordered to shoot a crusher 10 cells away (in the SG-60's range of 10.5,
--     out of the minigun's 9). The crusher must be hurt before the minigun is bought and untouched after it.
-- The medic, engineer, skirmisher, rocketeer and field commander stand there too, so a broken weapon condition on any of them fails the load.
-- Then the second rungs: the T-90 SMG needs the M25, and the sniper climbs SVD, TX-8, M42C in that order only (each is refused until the one before is held).
-- And the shotgun's TX-15 before the SH-410, the flamer's X-Napalm, and the three armour tiers (each refused until the one before is held).
-- Prints "TEST upgrade-ladders PASS" or "TEST upgrade-ladders FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	marines.Cash = 12000

	local gunner = marines.GetActorsByType("machinegunner")[1]
	local crusher = xenos.GetActorsByType("crusher")[1]
	-- A second one, untouched until the minigun check (the first may be dead by then).
	local fresh = xenos.GetActorsByType("crusher")[2]
	fresh.Stance = "HoldFire"
	gunner.Stance = "HoldFire"
	crusher.Stance = "HoldFire"
	local max = crusher.MaxHealth

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
			print("TEST upgrade-ladders PASS")
		else
			print("TEST upgrade-ladders FAIL (" .. table.concat(problems, "; ") .. ")")
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

	local function volley(target, then_)
		gunner.Attack(target, false, false)
		Trigger.AfterDelay(150, function() then_(target.IsDead or target.Health < max) end)
	end

	local names = { "upgrade-smg-m25", "upgrade-shotgun-tx15", "upgrade-mg-minigun", "upgrade-rocket-heavy" }

	Trigger.AfterDelay(60, function()
		volley(crusher, function(hurt)
			check(hurt, "the SG-60 did not reach a crusher 10 cells away")
			for _, n in ipairs(names) do
				check(marines.QueueUnit(n), n .. " could not be queued")
			end
			waitFor("upgrade-rocket-heavy", 3000, function()
				for _, n in ipairs(names) do
					check(marines.HasPrerequisites({ n }), n .. " not held")
					check(not marines.QueueUnit(n), n .. " bought twice")
				end
				check(not marines.QueueUnit("upgrade-sniper-tx8"), "tx8 bought before svd")
				check(not marines.QueueUnit("upgrade-sniper-m42c"), "m42c bought before tx8")
				check(marines.QueueUnit("upgrade-smg-t90"), "t90 could not be queued after m25")
				check(marines.QueueUnit("upgrade-sniper-svd"), "svd could not be queued")
				waitFor("upgrade-sniper-svd", 1500, function()
					check(not marines.QueueUnit("upgrade-sniper-m42c"), "m42c bought before tx8")
					check(marines.QueueUnit("upgrade-sniper-tx8"), "tx8 could not be queued after svd")
					waitFor("upgrade-sniper-tx8", 1500, function()
						check(marines.QueueUnit("upgrade-sniper-m42c"), "m42c could not be queued after tx8")
						waitFor("upgrade-sniper-m42c", 2000, function()
							waitFor("upgrade-smg-t90", 600, function()
								check(not marines.QueueUnit("upgrade-armor-2"), "armour II bought before I")
								check(not marines.QueueUnit("upgrade-armor-3"), "armour III bought before II")
								check(marines.QueueUnit("upgrade-shotgun-sh410"), "sh410 could not be queued after tx15")
								check(marines.QueueUnit("upgrade-flamer-xnapalm"), "x-napalm could not be queued")
								check(marines.QueueUnit("upgrade-armor-1"), "armour I could not be queued")
								waitFor("upgrade-armor-1", 1500, function()
									check(marines.QueueUnit("upgrade-armor-2"), "armour II could not be queued after I")
									waitFor("upgrade-armor-2", 1500, function()
										check(marines.QueueUnit("upgrade-armor-3"), "armour III could not be queued after II")
										waitFor("upgrade-armor-3", 2000, function()
											waitFor("upgrade-shotgun-sh410", 1500, function()
												waitFor("upgrade-flamer-xnapalm", 1500, function()
													local before = fresh.Health
													volley(fresh, function()
														check(fresh.Health >= before, "the minigun hit a crusher 10 cells away")
														finish()
													end)
												end)
											end)
										end)
									end)
								end)
							end)
						end)
					end)
				end)
			end)
		end)
	end)
end
