-- Scenario test (see mod/test_scenarios.sh): the Skirmish AI, set on the xeno player by the map, should spend its cash on
-- units from its silo. Prints "TEST ai PASS" or "TEST ai FAIL". It polls so that it finishes as soon as three exist.
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

	local function poll(ticks)
		if reported then
			return
		end
		local units = army()
		local count = #units
		if count >= 3 then
			reported = true
			print("TEST ai PASS (" .. count .. " xeno units by tick " .. ticks .. ", cash " .. xenos.Cash .. ")")
		elseif ticks >= 1000 then
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
