-- Scenario test: the xeno AI uses a caste ability by itself. The crusher holds fire, so only its Stomp can hurt the marines next to it.
-- Prints "TEST ai-abilities PASS" or "TEST ai-abilities FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines").GetActorsByType("rifleman")
	local start = {}
	for i, m in ipairs(marines) do
		start[i] = m.Health
	end
	local function poll(ticks)
		if reported then
			return
		end
		local hurt = 0
		for i, m in ipairs(marines) do
			if m.IsDead or m.Health < start[i] then
				hurt = hurt + 1
			end
		end
		if hurt >= 2 then
			reported = true
			print("TEST ai-abilities PASS (" .. hurt .. " marines stomped by tick " .. ticks .. ")")
		elseif ticks >= 1200 then
			reported = true
			print("TEST ai-abilities FAIL (" .. hurt .. " marines hurt)")
		else
			Trigger.AfterDelay(20, function() poll(ticks + 20) end)
		end
	end
	Trigger.AfterDelay(20, function() poll(20) end)
end
