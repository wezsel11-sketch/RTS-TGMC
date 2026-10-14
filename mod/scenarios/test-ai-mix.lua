-- Scenario test: the Skirmish AI on the xeno side builds a mix of castes, not runners alone. It polls and passes once the xeno army
-- holds at least three different castes. Prints "TEST ai-mix PASS" or "TEST ai-mix FAIL".
local reported = false
local castes = { "runner", "hunter", "sentinel", "warrior", "queen", "spitter", "praetorian", "crusher", "ravager", "boiler", "drone" }

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")

	local function kinds()
		local seen, list = {}, {}
		for _, a in ipairs(xenos.GetActorsByTypes(castes)) do
			if not seen[a.Type] then
				seen[a.Type] = true
				table.insert(list, a.Type)
			end
		end
		return list
	end

	local function poll(ticks)
		if reported then
			return
		end
		local list = kinds()
		if ticks % 500 == 0 then
			print("STAT tick " .. ticks .. " castes " .. table.concat(list, ",") .. " cash " .. xenos.Cash)
		end
		if #list >= 3 then
			reported = true
			print("TEST ai-mix PASS (castes " .. table.concat(list, ",") .. " by tick " .. ticks .. ")")
		elseif ticks >= 4500 then
			reported = true
			print("TEST ai-mix FAIL (castes " .. table.concat(list, ",") .. " after " .. ticks .. " ticks, cash " .. xenos.Cash .. ")")
		else
			Trigger.AfterDelay(100, function() poll(ticks + 100) end)
		end
	end
	Trigger.AfterDelay(100, function() poll(100) end)
end
