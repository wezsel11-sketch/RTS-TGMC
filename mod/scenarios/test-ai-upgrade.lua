-- Scenario test: the Skirmish AI on the marine player, with an Armory standing, buys the rifle upgrades from the Upgrades tab on its own
-- (UpgradeBotModule in Bots.cs), the T-12 first and then the M412. Prints "TEST ai-upgrade PASS" or "TEST ai-upgrade FAIL".
-- It polls so that it finishes as soon as both are held.
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")

	local function poll(ticks)
		if reported then
			return
		end
		local t12 = marines.HasPrerequisites({ "upgrade-rifle-t12" })
		local m412 = marines.HasPrerequisites({ "upgrade-rifle-m412" })
		if t12 and m412 then
			reported = true
			print("TEST ai-upgrade PASS (both rifle upgrades by tick " .. ticks .. ", cash " .. marines.Cash .. ")")
		elseif ticks >= 9000 then
			reported = true
			print("TEST ai-upgrade FAIL (t12 " .. tostring(t12) .. ", m412 " .. tostring(m412) .. " after " .. ticks .. " ticks, cash " .. marines.Cash .. ")")
		else
			Trigger.AfterDelay(50, function() poll(ticks + 50) end)
		end
	end
	Trigger.AfterDelay(50, function() poll(50) end)
end
