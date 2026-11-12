-- Scenario test (see mod/test_scenarios.sh): the Skirmish AI, set on the xeno player by the map, should spend its cash on
-- units from its silo. Prints "TEST ai PASS" or "TEST ai FAIL". It polls so that it finishes as soon as three exist
-- or two have been hatched beside the queen.
local reported = false

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	-- Any unit counts (anything that moves): the bot picks from many castes.
	local function army()
		local units = {}
		for _, a in ipairs(xenos.GetActors()) do
			if not a.IsDead and a.HasProperty("Move") then table.insert(units, a) end
		end
		return units
	end

	-- Units the bot has hatched so far. Counting only the living fails a bot that hatched banelings and sent them to burst.
	local hatched = 0
	Trigger.OnAnyProduction(function(_, produced)
		if produced.Owner == xenos and produced.HasProperty("Move") then hatched = hatched + 1 end
	end)

	local function poll(ticks)
		if reported then
			return
		end
		local units = army()
		local count = math.max(#units, hatched + 1)
		if count >= 3 then
			reported = true
			print("TEST ai PASS (" .. count .. " xeno units by tick " .. ticks .. ", cash " .. xenos.Cash .. ")")
		elseif ticks >= 2000 then
			reported = true
			local types = {}
			for _, a in ipairs(units) do table.insert(types, a.Type) end
			print("TEST ai FAIL (" .. count .. " xeno units after " .. ticks .. " ticks, cash " .. xenos.Cash .. ": " .. table.concat(types, ", ") .. ")")
		else
			Trigger.AfterDelay(50, function() poll(ticks + 50) end)
		end
	end
	Trigger.AfterDelay(50, function() poll(50) end)
end
