-- Scenario test (see mod/test_scenarios.sh): every unit type dies, some killed as an explosion would (damage type
-- ExplosionDeath, which plays die-gib) and the rest plainly (which plays die). A death sequence the sheet lacks only throws
-- when the animation renders, so the script waits 100 ticks before reporting and test_scenarios.sh then checks for an
-- exception log. Warrior and Queen are in the explosion group on purpose: they must play their plain death, not nothing.
-- Prints "TEST gib PASS" once every unit is dead, or "TEST gib FAIL".
local done = false

WorldLoaded = function()
	local marines, xenos = Player.GetPlayer("Marines"), Player.GetPlayer("Xenos")
	local blasted = { "rifleman", "medic", "engineer" }
	local plain = { "smartgunner", "grenadier" }
	local xenoBlasted = { "runner", "hunter", "warrior", "queen" }
	local xenoPlain = { "sentinel", "drone" }
	local victims = {}

	local function take(player, names, damageType)
		for _, name in ipairs(names) do
			local actor = player.GetActorsByType(name)[1]
			table.insert(victims, { name = name, actor = actor, damageType = damageType })
		end
	end
	take(marines, blasted, "ExplosionDeath")
	take(marines, plain, nil)
	take(xenos, xenoBlasted, "ExplosionDeath")
	take(xenos, xenoPlain, nil)

	Trigger.AfterDelay(5, function()
		for _, v in ipairs(victims) do
			if v.damageType then
				v.actor.Kill(v.damageType)
			else
				v.actor.Kill()
			end
		end
	end)

	Trigger.AfterDelay(105, function()
		if done then
			return
		end
		done = true
		local alive = {}
		for _, v in ipairs(victims) do
			if not v.actor.IsDead then
				table.insert(alive, v.name)
			end
		end
		if #alive == 0 then
			print("TEST gib PASS (all " .. #victims .. " units died, " .. #blasted + #xenoBlasted .. " by explosion)")
		else
			print("TEST gib FAIL (still alive: " .. table.concat(alive, ", ") .. ")")
		end
	end)
end
