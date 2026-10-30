-- Scenario test: veterancy. A rifleman kills three weak runners (cost 50 each, 150 in all) and ranks up to Veteran, which takes kills worth
-- its own cost (100). Prints "TEST veterancy PASS" or "TEST veterancy FAIL".
WorldLoaded = function()
	local rifleman = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	local runners = Player.GetPlayer("Xenos").GetActorsByType("runner")
	Utils.Do(runners, function(r)
		r.Stance = "HoldFire"
		r.Health = 1
	end)

	local function poll(ticks)
		local alive = 0
		for _, r in ipairs(runners) do
			if not r.IsDead then
				alive = alive + 1
			end
		end

		if alive == 0 or ticks >= 500 then
			if alive == 0 and rifleman.Level >= 1 then
				print("TEST veterancy PASS (level " .. rifleman.Level .. ", experience " .. rifleman.Experience .. ")")
			else
				print("TEST veterancy FAIL (" .. alive .. " runners alive, level " .. rifleman.Level .. ", experience " .. rifleman.Experience .. ")")
			end
			return
		end

		Trigger.AfterDelay(10, function() poll(ticks + 10) end)
	end
	poll(0)
end
