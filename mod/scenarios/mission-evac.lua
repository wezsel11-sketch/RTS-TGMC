-- Evac: the marines hold their base against xeno waves for about eight and a half minutes, then the Alamo lands at the landing
-- zone and the xenos pour in without pause. Every marine on foot who reaches the ship boards it. The ship leaves 90 seconds after
-- landing, or earlier when the player selects it and presses Deploy (F). One marine aboard wins; an empty ship, or no marine left
-- and nothing to train one, loses.
--
-- The split agreed for the waves: this script decides when each wave comes, how big it is and which castes are in it; the xenos
-- decide where. Each wave goes for the marine asset with the most value for the least defence, as the xenos' ThreatMemory sees it
-- (the map gives the xenos full vision), and comes in from the edge nearest to it.
-- The map removes ConquestVictoryConditions, so this script owns the objective. Test scripts override Config through ConfigOverride.

Config =
{
	-- Edge cells the xenos come in from: north, east and south.
	spawnCells =
	{
		CPos.New(20, 2), CPos.New(32, 2), CPos.New(44, 2),
		CPos.New(61, 12), CPos.New(61, 24), CPos.New(61, 36),
		CPos.New(20, 45), CPos.New(32, 45), CPos.New(44, 45),
	},

	-- Ticks after the previous wave (the first from the start), the units, and the payout when the wave is survived (paid as the
	-- next wave comes, or at landing for the last). No two alike: rushes, stealth, spit, armour, artillery.
	waves =
	{
		{ delay = 1500, pay = 300, units = { { "runner", 6 } } },
		{ delay = 1350, pay = 350, units = { { "hunter", 5 }, { "runner", 3 } } },
		{ delay = 1350, pay = 400, units = { { "sentinel", 4 }, { "spitter", 3 }, { "runner", 4 } } },
		{ delay = 1350, pay = 450, units = { { "warrior", 4 }, { "hunter", 4 } } },
		{ delay = 1350, pay = 500, units = { { "runner", 12 }, { "sentinel", 4 } } },
		{ delay = 1350, pay = 550, units = { { "crusher", 2 }, { "warrior", 4 }, { "spitter", 4 } } },
		{ delay = 1350, pay = 600, units = { { "boiler", 2 }, { "hunter", 6 }, { "sentinel", 6 } } },
		{ delay = 1350, pay = 650, units = { { "praetorian", 2 }, { "crusher", 2 }, { "runner", 10 }, { "spitter", 6 } } },
	},

	-- Ticks after the last wave before the Alamo lands, and how long it waits.
	landDelay = 1350,
	shuttleWait = 2250,
	-- The ship's centre cell (its 11 by 21 cells stand around it).
	shuttleCell = CPos.New(44, 24),

	-- During the evac: a pack every this many ticks, picked from these castes.
	assaultInterval = 60,
	assaultPack = 3,
	assaultTypes = { "runner", "runner", "hunter", "warrior", "sentinel", "spitter" },

	-- Marine assets a wave may go for, and how far around one counts as its defence.
	targetTypes = { "miner", "sentry-turret", "cade", "vendor", "cryo-pod", "mortar-emplacement", "armory", "medbay", "workshop", "ordnance-depot" },
	defenceRadius = 6,

	checkInterval = 25,
}

-- Marines on foot: they board. Mechs, turrets and buildings stay behind.
BoardTypes = { "rifleman", "medic", "engineer", "synth", "skirmisher", "smartgunner", "sniper", "rocketeer", "blademan", "mortarman",
	"flamer", "machinegunner", "bomber", "squad_leader", "field_commander", "grenadier", "heavygunner", "demolitionist" }
Producers = { "cryo-pod", "vendor" }

Finished = false
WavesSent = 0
Aboard = 0
NextEvent = 0
Shuttle = nil

Contains = function(list, value)
	for _, v in ipairs(list) do
		if v == value then return true end
	end
	return false
end

Expand = function(group)
	local types = {}
	for _, entry in ipairs(group) do
		for _ = 1, entry[2] do
			table.insert(types, entry[1])
		end
	end
	return types
end

Distance = function(a, b)
	return math.abs(a.X - b.X) + math.abs(a.Y - b.Y)
end

-- The marine asset with the most value for the least defence the xenos remember around it. Its own value is not its defence.
WeakestTarget = function()
	local best, bestScore = nil, -1
	for _, a in ipairs(Marines.GetActorsByTypes(Config.targetTypes)) do
		if not a.IsDead then
			local value = Actor.Cost(a.Type)
			local defence = math.max(0, Xenos.ThreatNear(a.Location, Config.defenceRadius) - value)
			local score = value / (1 + defence)
			if score > bestScore then
				best, bestScore = a, score
			end
		end
	end
	return best
end

NearestSpawn = function(cell)
	local best = Config.spawnCells[1]
	for _, c in ipairs(Config.spawnCells) do
		if Distance(c, cell) < Distance(best, cell) then best = c end
	end
	return best
end

-- Any marine left to fight: the base first, then whoever is out in the field.
AnyMarineCell = function()
	local all = Marines.GetActorsByTypes(Producers)
	if #all == 0 then all = Marines.GetActorsByTypes(BoardTypes) end
	if #all > 0 then return all[1].Location end
	return nil
end

Hunt = function(actor, cell)
	if actor.IsDead then return end
	local target = cell or AnyMarineCell()
	if target ~= nil then actor.AttackMove(target) end
	-- Done with its target: on to whatever marine is left.
	Trigger.OnIdle(actor, function(a)
		local c = AnyMarineCell()
		if c ~= nil and not a.IsDead then a.AttackMove(c) end
	end)
end

Spawn = function(types, from, to)
	for i, unitType in ipairs(types) do
		Trigger.AfterDelay(i * 6, function()
			if Finished then return end
			Reinforcements.Reinforce(Xenos, { unitType }, { from }, 0, function(actor) Hunt(actor, to) end)
		end)
	end
end

Pay = function(amount)
	Marines.Cash = Marines.Cash + amount
	Media.DisplayMessage("Wave survived: " .. amount .. " requisition", "Command")
end

SendWave = function(index)
	if Finished then return end
	if index > 1 then Pay(Config.waves[index - 1].pay) end
	local wave = Config.waves[index]
	WavesSent = index
	local target = WeakestTarget()
	local cell = target ~= nil and target.Location or AnyMarineCell() or Config.shuttleCell
	LastWaveTarget = target
	LastWaveSpawn = NearestSpawn(cell)
	Media.PlaySpeechNotification(Marines, index == #Config.waves and "WaveDistress" or "WaveIncoming")
	Spawn(Expand(wave.units), LastWaveSpawn, cell)

	local nextWave = Config.waves[index + 1]
	if nextWave ~= nil then
		NextEvent = DateTime.GameTime + nextWave.delay
		Trigger.AfterDelay(nextWave.delay, function() SendWave(index + 1) end)
	else
		NextEvent = DateTime.GameTime + Config.landDelay
		Trigger.AfterDelay(Config.landDelay, Land)
	end
end

ShuttleCells = function()
	local cells = {}
	local c = Config.shuttleCell
	for x = c.X - 5, c.X + 5 do
		for y = c.Y - 10, c.Y + 10 do
			table.insert(cells, CPos.New(x, y))
		end
	end
	return cells
end

Board = function(actor)
	if Finished or Shuttle == nil or actor.IsDead or actor.Owner ~= Marines or not Contains(BoardTypes, actor.Type) then return end
	Aboard = Aboard + 1
	actor.Destroy()
end

Land = function()
	if Finished then return end
	Pay(Config.waves[#Config.waves].pay)
	Shuttle = Actor.Create("alamo", true, { Owner = Marines, Location = Config.shuttleCell })
	Media.PlaySpeechNotification(Marines, "WaveDistress")
	Media.DisplayMessage("The Alamo is down at the landing zone. Get your marines aboard!", "Command")
	Shuttle.GrantCondition("doors-opening", 18)
	Trigger.AfterDelay(18, function()
		if Shuttle ~= nil and Shuttle.IsInWorld then Shuttle.GrantCondition("doors-open") end
	end)
	NextEvent = DateTime.GameTime + Config.shuttleWait
	Trigger.OnEnteredFootprint(ShuttleCells(), function(a) Board(a) end)
	-- Marines already standing on the pad board at once.
	local c = Config.shuttleCell
	for _, a in ipairs(Map.ActorsInBox(Map.CenterOfCell(CPos.New(c.X - 5, c.Y - 10)), Map.CenterOfCell(CPos.New(c.X + 5, c.Y + 10)))) do
		Board(a)
	end
	Trigger.OnRemovedFromWorld(Shuttle, function() TakeOff() end)
	Trigger.AfterDelay(Config.shuttleWait, function()
		if Shuttle ~= nil and Shuttle.IsInWorld then Shuttle.GrantCondition("launch") end
	end)
	Assault()
end

-- From landing to take-off the xenos never stop: packs from every edge, all for the landing zone.
Assault = function()
	if Finished then return end
	local types = {}
	for _ = 1, Config.assaultPack do
		table.insert(types, Utils.Random(Config.assaultTypes))
	end
	Spawn(types, Utils.Random(Config.spawnCells), Config.shuttleCell)
	Trigger.AfterDelay(Config.assaultInterval, Assault)
end

TakeOff = function()
	if Finished then return end
	Finished = true
	if Aboard > 0 then
		UserInterface.SetMissionText("The Alamo is away with " .. Aboard .. " marine" .. (Aboard == 1 and "" or "s") .. " aboard")
		Marines.MarkCompletedObjective(Objective)
	else
		UserInterface.SetMissionText("The Alamo left without a single marine")
		Marines.MarkFailedObjective(Objective)
	end
end

Clock = function(ticks)
	local seconds = math.max(0, math.floor(ticks / 25))
	return math.floor(seconds / 60) .. ":" .. string.format("%02d", seconds % 60)
end

Check = function()
	if Finished then return end

	if #Marines.GetActorsByTypes(BoardTypes) == 0 and Aboard == 0 and #Marines.GetActorsByTypes(Producers) == 0 then
		Finished = true
		UserInterface.SetMissionText("The marines have fallen")
		Marines.MarkFailedObjective(Objective)
		return
	end

	local left = Clock(NextEvent - DateTime.GameTime)
	if Shuttle ~= nil then
		UserInterface.SetMissionText("Alamo leaves in " .. left .. "   Aboard: " .. Aboard)
	elseif WavesSent < #Config.waves then
		UserInterface.SetMissionText("Wave " .. (WavesSent + 1) .. " of " .. #Config.waves .. " in " .. left)
	else
		UserInterface.SetMissionText("Evac lands in " .. left)
	end
	Trigger.AfterDelay(Config.checkInterval, Check)
end

WorldLoaded = function()
	if ConfigOverride ~= nil then
		ConfigOverride(Config)
	end
	Marines = Player.GetPlayer("Marines")
	Xenos = Player.GetPlayer("Xenos")
	Objective = Marines.AddPrimaryObjective("Hold until the evac, then get at least one marine aboard the Alamo")
	NextEvent = Config.waves[1].delay
	Trigger.AfterDelay(Config.waves[1].delay, function() SendWave(1) end)
	Trigger.AfterDelay(Config.checkInterval, Check)
	if AfterStart ~= nil then
		AfterStart()
	end
end
