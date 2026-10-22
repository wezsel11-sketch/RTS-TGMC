-- Scenario test (see mod/test_scenarios.sh): armour does not stop acid, the gas mask of armour upgrade I cuts gas damage.
-- Acid gas burns one rifleman with no upgrades, then armour I is bought and the same gas burns a second one.
-- The masked marine must lose well under half what the bare one lost (the mask takes it to 35%; armour I alone would be 87%).
-- Prints "TEST gasmask PASS" or "TEST gasmask FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	marines.Cash = 3000
	local a = marines.GetActorsByType("rifleman")[1]
	local b = marines.GetActorsByType("rifleman")[2]
	a.Stance = "HoldFire"
	b.Stance = "HoldFire"

	local bareLoss = 0
	local function lost(m, from) return from - m.Health end
	local function burn(m, then_)
		local start = m.Health
		local g = Actor.Create("acid-gas", true, { Owner = xenos, Location = m.Location })
		-- Ordered, not left to auto-target: the point is the damage the marine takes, not the cloud's target scan.
		Trigger.AfterDelay(2, function() g.Attack(m, true, true) end)
		Trigger.AfterDelay(220, function() then_(lost(m, start)) end)
	end
	local function finish(ok, msg)
		if reported then return end
		reported = true
		print("TEST gasmask " .. (ok and "PASS" or "FAIL") .. " (" .. msg .. ")")
	end
	local function waitFor(ticks)
		if marines.HasPrerequisites({ "upgrade-armor-1" }) then
			burn(b, function(masked)
				finish(masked * 2 < bareLoss, "bare lost " .. bareLoss .. ", masked lost " .. masked)
			end)
		elseif ticks <= 0 then
			finish(false, "armour I never arrived")
		else
			Trigger.AfterDelay(10, function() waitFor(ticks - 10) end)
		end
	end

	Trigger.AfterDelay(30, function()
		burn(a, function(bare)
			bareLoss = bare
			if bare < 20 then finish(false, "bare marine lost only " .. bare) return end
			marines.QueueUnit("upgrade-armor-1")
			waitFor(1500)
		end)
	end)
end
