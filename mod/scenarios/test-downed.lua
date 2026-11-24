-- Scenario test: TGMC's downed state. A runner brings a rifleman down; what happens next depends on the map:
--   scenario-downed-revive: the runner is removed and a corpsman heals the downed marine until he stands up again.
--   scenario-downed-cocoon: the runner finishes him off, a cocoon of the hive's takes his place, and later a larva comes out of it.
--   scenario-downed-bleed:  the runner is removed and nobody helps: he bleeds out and is gone.
-- The mode is the map's Mode variable (set by the map's own script). Prints "TEST downed-<mode> PASS" or "... FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local victim = nil
	for _, a in ipairs(marines.GetActorsByType("rifleman")) do
		if a.Location.X == 10 then
			victim = a
		end
	end
	local runner = xenos.GetActorsByType("runner")[1]
	victim.Stance = "HoldFire"
	victim.Health = 20
	Trigger.AfterDelay(10, function() runner.Attack(victim, true, true) end)
	local downedAt = nil
	local cocoonAt = nil
	local name = "downed-" .. Mode

	local function finish(ok, why)
		print("TEST " .. name .. " " .. (ok and "PASS" or "FAIL") .. " (" .. why .. ")")
	end

	Trigger.OnKilled(victim, function()
		downedAt = DateTime.GameTime
		-- Removed, not killed: a dying xeno's acid blood would burn the body and cut the bleed-out short.
		if Mode ~= "cocoon" and not runner.IsDead then
			runner.Destroy()
		end
	end)

	local function look(ticks)
		local downed = #marines.GetActorsByType("downed")
		local riflemen = #marines.GetActorsByType("rifleman")
		local cocoons = #xenos.GetActorsByType("cocoon")
		local larvae = #xenos.GetActorsByType("larva")
		if downedAt and not cocoonAt and cocoons > 0 then
			cocoonAt = ticks
		end

		if Mode == "revive" and downedAt and downed == 0 and riflemen == 2 then
			-- He gets up hurt, and only after a few heals: the body starts at half health and bleeds while it is healed.
			local up = nil
			for _, a in ipairs(marines.GetActorsByType("rifleman")) do
				if a.Location.X < 20 then
					up = a
				end
			end
			local ok = up ~= nil and up.Health < up.MaxHealth and ticks - downedAt > 60
			finish(ok, "down at " .. downedAt .. ", up again at " .. ticks .. " with " .. (up and up.Health or -1) .. " health")
			return
		elseif Mode == "cocoon" and cocoonAt and larvae > 0 and cocoons == 0 then
			finish(true, "cocooned at " .. cocoonAt .. ", larva at " .. ticks)
			return
		elseif Mode == "bleed" and downedAt and downed == 0 then
			-- 50 health at 1 every 12 ticks: about 600 ticks.
			local ok = riflemen == 1 and ticks - downedAt > 500
			finish(ok, "down at " .. downedAt .. ", gone at " .. ticks .. ", riflemen " .. riflemen)
			return
		elseif ticks > 2000 then
			finish(false, "timed out: downedAt=" .. tostring(downedAt) .. " downed=" .. downed .. " riflemen=" .. riflemen ..
				" cocoons=" .. cocoons .. " larvae=" .. larvae)
			return
		end

		Trigger.AfterDelay(5, function() look(ticks + 5) end)
	end
	look(0)
end
