-- AI tuning on a full-size map: both sides run the Skirmish AI. It prints a status line every 1000 ticks (army sizes, structure
-- counts, the distance between the two armies, the fields each side holds) and the winner when
-- there is one. Not a pass/fail test: read the STAT lines. Prints "TEST aimap DONE" at the end (a win, or MaxTicks).
MaxTicks = 40000
local reported = false

-- Every unit that moves and fights (not a drone or a building), so new units count without editing a list.
local function army(player)
	return Utils.Where(player.GetActors(), function(a) return a.HasProperty("Move") and a.HasProperty("Attack") and a.Type ~= "drone" end)
end

-- Distress: who holds the nuke.
local function nukeOwner(marines, xenos)
	if #marines.GetActorsByTypes({ "nuke" }) > 0 then return "marines" end
	if #xenos.GetActorsByTypes({ "nuke" }) > 0 then return "xenos" end
	return "-"
end

local function mean(player)
	local actors = army(player)
	if #actors == 0 then
		return nil, 0
	end
	local sx, sy = 0, 0
	for _, a in ipairs(actors) do
		sx = sx + a.Location.X
		sy = sy + a.Location.Y
	end
	return { x = sx / #actors, y = sy / #actors }, #actors
end

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local structures = { "cryo-pod", "vendor", "sentry-turret", "resin-silo", "mini-silo", "resin-turret", "miner", "armory", "ordnance-depot",
		"weed-node", "evolution-tower", "maturity-tower", "forward-hive", "workshop", "mortar-emplacement", "corrupted-miner", "som-beacon" }
	local fields = { "miner", "corrupted-miner" }

	local function finish(winner, ticks)
		if reported then
			return
		end
		reported = true
		print("TEST aimap DONE (" .. winner .. " at tick " .. ticks .. ")")
	end

	local ticks = 0
	local function status()
		if reported then
			return
		end
		local mm, mc = mean(marines)
		local xm, xc = mean(xenos)
		local gap = (mm and xm) and math.floor(math.sqrt((mm.x - xm.x) ^ 2 + (mm.y - xm.y) ^ 2)) or -1
		print(string.format("STAT tick=%d marines: army=%d at %d,%d structures=%d fields=%d cash=%d | xenos: army=%d at %d,%d structures=%d fields=%d cash=%d disks=%d | gap=%d nuke=%s", ticks,
			mc, mm and math.floor(mm.x) or -1, mm and math.floor(mm.y) or -1, #marines.GetActorsByTypes(structures), #marines.GetActorsByTypes(fields), marines.Cash,
			xc, xm and math.floor(xm.x) or -1, xm and math.floor(xm.y) or -1, #xenos.GetActorsByTypes(structures), #xenos.GetActorsByTypes(fields), xenos.Cash, #marines.GetActorsByTypes({ "disk-terminal" }), gap, nukeOwner(marines, xenos)))
		for _, t in ipairs(Map.ActorsInWorld) do
			if (t.Type == "disk-terminal" or t.Type == "nuke") and not t.IsDead then
				local near, idle = 0, 0
				for _, a in ipairs(Map.ActorsInCircle(t.CenterPosition, WDist.FromCells(6))) do
					if a.Owner == marines and a.HasProperty("Move") then
						near = near + 1
						if a.IsIdle then idle = idle + 1 end
					end
				end
				print(string.format("OBJ tick=%d %s at %d,%d owner=%s marines-in-6=%d idle=%d", ticks, t.Type, t.Location.X, t.Location.Y, t.Owner.InternalName, near, idle))
			end
		end
		if ticks >= MaxTicks then
			finish("nobody", ticks)
			return
		end
		ticks = ticks + 1000
		Trigger.AfterDelay(1000, status)
	end
	status()

	Trigger.OnPlayerWon(marines, function() finish("marines", ticks) end)
	Trigger.OnPlayerWon(xenos, function() finish("xenos", ticks) end)
end
