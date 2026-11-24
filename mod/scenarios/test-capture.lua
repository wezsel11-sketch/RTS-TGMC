-- Scenario test: ore fields are capture points for every side.
--   1. A drone covers a free field in resin: it becomes the xenos' corrupted miner and pays biomass.
--   2. Riflemen knock the corrupted miner down: it is a free field again, never destroyed.
--   3. An engineer repairs that field: it is the marines' miner.
-- Prints "TEST capture PASS" or "TEST capture FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local neutral = Player.GetPlayer("Neutral")
	local drone = xenos.GetActorsByType("drone")[1]
	local engineer = marines.GetActorsByType("engineer")[1]
	local riflemen = marines.GetActorsByType("rifleman")
	local field = neutral.GetActorsByType("miner-field")[1]
	local step, paid = 1, false
	local at = {}
	engineer.Stance = "HoldFire"
	for _, r in ipairs(riflemen) do r.Stance = "HoldFire" end
	Trigger.AfterDelay(10, function() drone.Attack(field, true, true) end)

	local function fail(why, ticks)
		reported = true
		print("TEST capture FAIL (" .. why .. " by tick " .. ticks .. ", step " .. step .. ")")
	end

	local function poll(ticks)
		if reported then
			return
		end
		if step == 1 and #xenos.GetActorsByType("corrupted-miner") == 1 then
			step = 2
			at[1] = ticks
			local cash0 = xenos.Cash + xenos.Resources
			Trigger.AfterDelay(200, function()
				paid = xenos.Cash + xenos.Resources > cash0
				drone.Stop()
				drone.Move(CPos.New(2, 2))
				local corrupted = xenos.GetActorsByType("corrupted-miner")[1]
				-- 1 HP above the floor (25%): every hit must still knock it down (cutting hits to the room above the floor rounded them to 0).
				corrupted.Health = math.floor(corrupted.MaxHealth * 25 / 100) + 1
				Trigger.AfterDelay(100, function()
					if step == 2 and #xenos.GetActorsByType("corrupted-miner") > 0 then
						fail("the corrupted miner stuck 1 HP above its floor under rifle fire (" .. corrupted.Health .. " HP)", ticks)
					end
				end)
				for _, r in ipairs(riflemen) do
					if not r.IsDead then r.Attack(corrupted, true, true) end
				end
			end)
		elseif step == 2 and paid and #xenos.GetActorsByType("corrupted-miner") == 0 then
			local free = neutral.GetActorsByType("miner-field")
			if #free ~= 1 then
				return fail("the corrupted miner is gone and no free field is left", ticks)
			end
			step = 3
			at[2] = ticks
			for _, r in ipairs(riflemen) do
				if not r.IsDead then r.Stop() end
			end
			-- Not forced: a forced attack fires the engineer's shotgun at the field as well as the torch.
			engineer.Attack(free[1], true, false)
		elseif step == 3 and #marines.GetActorsByType("miner") == 1 then
			reported = true
			print("TEST capture PASS (corrupted by tick " .. at[1] .. ", paid biomass, freed by " .. at[2] .. ", claimed by " .. ticks .. ")")
			return
		end
		if ticks >= 5000 then
			local f = neutral.GetActorsByType("miner-field")[1]
			fail("not finished, biomass paid " .. tostring(paid) .. ", engineer dead " .. tostring(engineer.IsDead) .. ", field health " ..
				(f and f.Health or -1) .. " of " .. (f and f.MaxHealth or -1), ticks)
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
