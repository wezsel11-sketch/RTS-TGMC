-- Scenario test (see mod/test_scenarios.sh): a Research Lab makes marines tougher. A Crusher slams an idle rifleman and the
-- test records what the first blow took off. Without a lab (mode "off") that is the whole 48 points; with one (mode "on")
-- marines take 15% less damage, so it is about 41.
-- Prints "TEST research-__MODE__ PASS" or "TEST research-__MODE__ FAIL".
local Mode = "__MODE__"

WorldLoaded = function()
	local marine = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	local crusher = Player.GetPlayer("Xenos").GetActorsByType("crusher")[1]
	marine.Stance = "HoldFire"
	local max = marine.MaxHealth
	local done = false
	local function poll(tick)
		if done then
			return
		end
		if marine.IsDead or marine.Health < max or tick >= 300 then
			done = true
			local lost = marine.IsDead and max or (max - marine.Health)
			local lo, hi = 46, 50
			if Mode == "on" then
				lo, hi = 38, 44
			end
			print("TEST research-" .. Mode .. ((lost >= lo and lost <= hi) and " PASS" or " FAIL") .. " (the first blow took " .. lost .. " health; expected " .. lo .. " to " .. hi .. "; the Crusher is at " .. (crusher.IsDead and "dead" or (crusher.Location.X .. "," .. crusher.Location.Y)) .. ")")
			return
		end
		Trigger.AfterDelay(1, function() poll(tick + 1) end)
	end
	-- the order needs the marine to be revealed to the xenos, which takes a few ticks after the world loads
	Trigger.AfterDelay(15, function()
		crusher.Attack(marine)
		poll(1)
	end)
end
