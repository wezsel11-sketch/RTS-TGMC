-- Scenario test (see mod/test_scenarios.sh): a full match with the Skirmish AI on both sides, on the Landing Zone layout
-- at the fastest game speed. It prints a status line every 500 ticks (for tuning) and, when someone wins, the winner and
-- the tick. PASS means a winner emerged between MinTicks and MaxTicks: not a rout, and not a stalemate.
-- Prints "TEST aivai PASS" or "TEST aivai FAIL".
MinTicks = 3000
MaxTicks = 20000
local reported = false

local function count(player, types)
	return #player.GetActorsByTypes(types)
end

-- Mean x cell of a player's units, so the log shows how far an army has advanced (marines start near x=7, xenos near x=30).
local function meanX(player, types)
	local actors = player.GetActorsByTypes(types)
	if #actors == 0 then
		return -1
	end
	local sum = 0
	for _, a in ipairs(actors) do
		sum = sum + a.Location.X
	end
	return math.floor(sum / #actors)
end

-- Lowest health percentage among a player's structures.
local function weakest(player, types)
	local low = 100
	for _, a in ipairs(player.GetActorsByTypes(types)) do
		low = math.min(low, math.floor(100 * a.Health / a.MaxHealth))
	end
	return low
end

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local marineArmy = { "rifleman", "medic", "engineer" }
	local xenoArmy = { "runner", "hunter", "sentinel", "drone" }
	local structures = { "cryo-pod", "vendor", "sentry-turret", "resin-silo", "mini-silo", "resin-turret" }

	local function finish(winner, ticks)
		if reported then
			return
		end
		reported = true
		local ok = ticks >= MinTicks and ticks <= MaxTicks
		print("TEST aivai " .. (ok and "PASS" or "FAIL") .. " (" .. winner .. " won at tick " .. ticks .. ", limits " .. MinTicks .. " to " .. MaxTicks .. ")")
	end

	local ticks = 0
	local function status()
		if reported then
			return
		end
		print(string.format("STAT tick=%d marines: army=%d x=%d structures=%d weakest=%d%% cash=%d | xenos: army=%d x=%d structures=%d weakest=%d%% cash=%d", ticks,
			count(marines, marineArmy), meanX(marines, marineArmy), count(marines, structures), weakest(marines, structures), marines.Cash,
			count(xenos, xenoArmy), meanX(xenos, xenoArmy), count(xenos, structures), weakest(xenos, structures), xenos.Cash))
		if ticks >= MaxTicks then
			finish("nobody", ticks)
			return
		end
		ticks = ticks + 500
		Trigger.AfterDelay(500, status)
	end
	status()

	Trigger.OnPlayerWon(marines, function() finish("marines", ticks) end)
	Trigger.OnPlayerWon(xenos, function() finish("xenos", ticks) end)
end
