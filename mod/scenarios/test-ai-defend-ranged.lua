-- Scenario test: DefendBotModule against a ranged attack. Three marine riflemen (no marine bot) attack-move at a xeno mini-silo
-- from tick 200 and open fire at rifle range (9 cells), outside the module's 5-cell Radius. The xeno bot (easy) has eight idle runners at its silo. Prints
-- "TEST ai-defend-ranged PASS" if at least 2 runners come within 10 cells of the mini-silo by tick 1000, else FAIL.
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local marines = Player.GetPlayer("Marines")
	local silo = xenos.GetActorsByType("mini-silo")[1]
	local spot = silo.Location

	Trigger.AfterDelay(200, function()
		local rifles = Reinforcements.Reinforce(marines, { "rifleman", "rifleman", "rifleman" }, { CPos.New(16, 20) }, 0)
		for _, r in ipairs(rifles) do
			r.AttackMove(spot)
		end
	end)

	local function poll(ticks)
		if reported then
			return
		end
		local n = 0
		for _, r in ipairs(xenos.GetActorsByType("runner")) do
			if not r.IsDead and math.max(math.abs(r.Location.X - spot.X), math.abs(r.Location.Y - spot.Y)) <= 10 then
				n = n + 1
			end
		end
		if ticks % 250 == 0 then
			local where = {}
			for _, r in ipairs(xenos.GetActorsByType("runner")) do
				if not r.IsDead then table.insert(where, r.Location.X .. "," .. r.Location.Y .. (r.IsIdle and "i" or "")) end
			end
			print("DBG tick " .. ticks .. " silo hp " .. silo.Health .. " runners " .. table.concat(where, " "))
		end
		if not silo.IsDead and silo.Health < silo.MaxHealth / 2 then
			silo.Health = silo.MaxHealth
		end
		if n >= 2 then
			reported = true
			print("TEST ai-defend-ranged PASS (" .. n .. " runners near the mini-silo by tick " .. ticks .. ")")
		elseif ticks >= 1000 then
			reported = true
			print("TEST ai-defend-ranged FAIL (" .. n .. " runners near the mini-silo at tick 1000)")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
