-- Scenario test: the marine AI uses its support powers by itself: a sentry or mortar dropped by pod, a supply crate, a smoke screen.
-- Prints "TEST ai-support PASS" or "TEST ai-support FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local function seen(name)
		return #marines.GetActorsByType(name) > 0
	end
	local function poll(ticks)
		if reported then
			return
		end
		local found = {}
		for _, n in ipairs({ "sentry-turret", "mortar-emplacement", "supply-crate", "smoke-screen" }) do
			if seen(n) then
				found[#found + 1] = n
			end
		end
		if #found >= 2 then
			reported = true
			print("TEST ai-support PASS (" .. table.concat(found, ", ") .. " by tick " .. ticks .. ")")
		elseif ticks >= 3000 then
			reported = true
			print("TEST ai-support FAIL (only " .. table.concat(found, ", ") .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
