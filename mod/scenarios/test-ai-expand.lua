-- Scenario test: both Skirmish AIs, fed with cash and kept from fighting, should use the late-game content: the xeno bot a Forward
-- Hive and Resin Traps, the marine bot a Workshop and Mortar or Artillery Emplacements, and both a spread of heavier units.
-- Prints "TEST ai-expand PASS" or "TEST ai-expand FAIL".
MaxTicks = 16000
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local seen = {}

	local function note(player, types)
		for _, a in ipairs(player.GetActorsByTypes(types)) do
			seen[a.Type] = true
		end
	end

	local function poll(ticks)
		if reported then
			return
		end
		marines.Cash = marines.Cash + 300
		xenos.Cash = xenos.Cash + 300
		note(marines, { "workshop", "mortar-emplacement", "artillery-emplacement", "sniper", "rocketeer", "blademan", "mortarman", "flamer", "machinegunner", "heavygunner", "demolitionist", "mech" })
		note(xenos, { "forward-hive", "resin-trap", "defiler", "boiler", "carrier", "warlock", "shrike", "widow", "wraith", "bull", "behemoth" })
		local ok = seen["forward-hive"] and seen["resin-trap"] and (seen["mortar-emplacement"] or seen["artillery-emplacement"]) and seen["flamer"]
		if ticks % 2000 == 0 then
			local list = {}
			for k, _ in pairs(seen) do table.insert(list, k) end
			table.sort(list)
			print("STAT tick " .. ticks .. " seen " .. table.concat(list, ","))
		end
		if ok then
			reported = true
			print("TEST ai-expand PASS (by tick " .. ticks .. ")")
		elseif ticks >= MaxTicks then
			reported = true
			local list = {}
			for k, _ in pairs(seen) do table.insert(list, k) end
			table.sort(list)
			print("TEST ai-expand FAIL (seen " .. table.concat(list, ",") .. ")")
		else
			Trigger.AfterDelay(100, function() poll(ticks + 100) end)
		end
	end
	Trigger.AfterDelay(100, function() poll(100) end)
end
