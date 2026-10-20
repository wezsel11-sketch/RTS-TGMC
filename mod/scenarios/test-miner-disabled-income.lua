-- Scenario test: a marine miner that xenos have disabled (brought to its floor) pays no income, and is not destroyed.
-- A hunter attacks the miner. Once the miner reaches its floor, cash is read, and after 1000 more ticks the gain must be under 24
-- (a disabled miner's CashTrickler is paused by miner-disabled). "TEST miner-disabled-income PASS" when the miner is still alive,
-- the floor was reached and nothing was paid; otherwise FAIL.
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local miner = marines.GetActorsByType("miner")[1]
	local hunter = xenos.GetActorsByType("hunter")[1]
	hunter.Attack(miner, true, true)

	local function finish(gained, ticks)
		reported = true
		local alive = not miner.IsDead
		print("TEST miner-disabled-income " .. ((alive and gained < 24) and "PASS" or "FAIL") .. " (alive " .. tostring(alive) ..
			", gained " .. gained .. " in 1000 ticks disabled, by tick " .. ticks .. ")")
	end

	local function poll(ticks)
		if reported then
			return
		end
		if miner.IsDead then
			reported = true
			print("TEST miner-disabled-income FAIL (miner destroyed by tick " .. ticks .. ")")
			return
		end
		-- The floor is 25% of 250; a few points of slack for the last hit.
		if miner.Health * 100 <= miner.MaxHealth * 30 then
			local cash0 = marines.Cash
			Trigger.AfterDelay(1000, function() finish(marines.Cash - cash0, ticks) end)
			return
		end
		if ticks >= 6000 then
			reported = true
			print("TEST miner-disabled-income FAIL (miner never reached its floor by tick " .. ticks .. ")")
		else
			Trigger.AfterDelay(25, function() poll(ticks + 25) end)
		end
	end
	Trigger.AfterDelay(25, function() poll(25) end)
end
