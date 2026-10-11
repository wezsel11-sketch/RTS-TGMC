-- Balance run (see mod/balance.sh): Hold the Line with a marine bot that stays home. It prints a status line every
-- 500 ticks and, when the game ends, "TEST holdline PASS (marines won ...)" or "TEST holdline PASS (marines lost ...)".
-- The wave script calls AfterStart from its WorldLoaded.
local reported = false

AfterStart = function()
	local army = { "rifleman", "medic", "engineer" }
	local structures = { "cryo-pod", "vendor", "sentry-turret" }
	local ticks = 0

	local function finish(result)
		if reported then
			return
		end
		reported = true
		print("TEST holdline PASS (marines " .. result .. " at tick " .. ticks .. ", wave " .. WavesSent .. " of " .. #Config.waves .. ")")
	end

	local function status()
		if reported then
			return
		end
		local xenoActors = Xenos.GetActorsByTypes(XenoTypes)
		local sumX, idle = 0, 0
		for _, a in ipairs(xenoActors) do
			sumX = sumX + a.Location.X
			if a.IsIdle then
				idle = idle + 1
			end
		end
		print(string.format("STAT tick=%d wave=%d marines: army=%d structures=%d cash=%d | xenos alive=%d meanx=%d idle=%d", ticks, WavesSent,
			#Marines.GetActorsByTypes(army), #Marines.GetActorsByTypes(structures), Marines.Cash, #xenoActors,
			#xenoActors > 0 and math.floor(sumX / #xenoActors) or -1, idle))
		if ticks >= 12000 then
			finish("held out (time limit)")
			return
		end
		ticks = ticks + 500
		Trigger.AfterDelay(500, status)
	end
	status()

	Trigger.OnPlayerWon(Marines, function() finish("won") end)
	Trigger.OnPlayerLost(Marines, function() finish("lost") end)
end
