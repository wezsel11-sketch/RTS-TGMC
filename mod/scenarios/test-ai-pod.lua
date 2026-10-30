-- Scenario test: the marine AI calls a drop pod on a cluster of hunters by itself, and the marines inside step out. Prints "TEST ai-pod PASS" or "TEST ai-pod FAIL".
-- A pod's marines are made by the power, not trained: every marine infantry that shows up without a producer counts as a pod arrival.
local reported = false
local seen = {}
local trained = {}
local arrived = 0

-- Lua gets a new handle for an actor on every call, so tables key it by its name and ID ("Actor (rifleman 42)").
local function key(a)
	return (tostring(a):gsub(" %(not in world%)", ""))
end

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	-- Standing still, hunters fade from sight and the AI cannot aim at what it cannot see: switch their stealth off.
	Utils.Do(Player.GetPlayer("Xenos").GetActorsByType("hunter"), function(h) h.UseAbility(1) end)
	-- The units on the map at the start are not arrivals.
	for _, t in ipairs({ "rifleman", "medic", "engineer" }) do
		Utils.Do(marines.GetActorsByType(t), function(a) seen[key(a)] = true end)
	end
	Trigger.OnAnyProduction(function(_, produced) trained[key(produced)] = true end)

	local function poll(ticks)
		if reported then
			return
		end
		for _, t in ipairs({ "rifleman", "medic", "engineer" }) do
			for _, a in ipairs(marines.GetActorsByType(t)) do
				if not seen[key(a)] then
					seen[key(a)] = true
					if not trained[key(a)] then
						arrived = arrived + 1
					end
				end
			end
		end
		if arrived >= 3 then
			reported = true
			print("TEST ai-pod PASS (" .. arrived .. " marines came by pod by tick " .. ticks .. ")")
		elseif ticks >= 2500 then
			reported = true
			print("TEST ai-pod FAIL (" .. arrived .. " marines came by pod)")
		else
			Trigger.AfterDelay(5, function() poll(ticks + 5) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
