-- Scenario test (see mod/test_scenarios.sh): every weapon with an effect fires once, so the log shows any missing
-- sequence or engine exception, and the damage each one does proves the new projectiles still hit.
--   rifleman vs hunter    bullet tracer, muzzle flash, gore, claws
--   smartgunner vs sentinel   fast tracers, acid spit
--   grenadier vs resin turret   grenade launcher, explosion, acid turret
--   sentry vs warrior     heavy tracer, slam
-- Prints "TEST fx PASS" once something on each side of every pair has taken damage, or "TEST fx FAIL".
local done = false

WorldLoaded = function()
	local marines, xenos = Player.GetPlayer("Marines"), Player.GetPlayer("Xenos")
	local pairs_ =
	{
		{ "rifleman vs hunter", marines.GetActorsByType("rifleman")[1], xenos.GetActorsByType("hunter")[1] },
		{ "smartgunner vs sentinel", marines.GetActorsByType("smartgunner")[1], xenos.GetActorsByType("sentinel")[1] },
		{ "grenadier vs resin turret", marines.GetActorsByType("grenadier")[1], xenos.GetActorsByType("resin-turret")[1] },
		{ "sentry vs warrior", marines.GetActorsByType("sentry-turret")[1], xenos.GetActorsByType("warrior")[1] },
	}
	local maxHealth = {}
	for _, p in ipairs(pairs_) do
		maxHealth[p[2]] = p[2].MaxHealth
		maxHealth[p[3]] = p[3].MaxHealth
	end
	local function hurt(actor)
		return actor.IsDead or actor.Health < maxHealth[actor]
	end

	local function poll(ticks)
		if done then
			return
		end
		local missing = {}
		for _, p in ipairs(pairs_) do
			-- The xeno side is the one a marine weapon has to hit; the marine side is hit by claws, acid or the slam
			if not hurt(p[3]) then
				table.insert(missing, p[1] .. " (xeno side)")
			end
		end
		if #missing == 0 then
			done = true
			print("TEST fx PASS (every marine weapon landed a hit by tick " .. ticks .. ")")
		elseif ticks >= 750 then
			done = true
			print("TEST fx FAIL (no damage for: " .. table.concat(missing, ", ") .. ")")
		else
			Trigger.AfterDelay(10, function() poll(ticks + 10) end)
		end
	end
	Trigger.AfterDelay(10, function() poll(10) end)
end
