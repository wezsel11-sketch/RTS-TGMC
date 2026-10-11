-- Hold the Line: the marines defend their base against timed waves of xenos from the east edge. They win by
-- destroying every xeno after the last wave and lose when they have no required units left.
-- The map removes ConquestVictoryConditions, so this script owns the objective. test-waves.lua overrides Config
-- through ConfigOverride.

Config =
{
	-- Edge cells the xeno units appear on, picked at random per unit.
	spawnCells = { CPos.New(38, 4), CPos.New(38, 9), CPos.New(38, 14), CPos.New(38, 19), CPos.New(38, 24) },

	-- Ticks to wait after the previous wave (the first is counted from the start) and the units in each, as
	-- { type, count } pairs. A tick is 40 ms.
	waves =
	{
		{ delay = 750,  units = { { "runner", 6 } } },
		{ delay = 900,  units = { { "runner", 8 }, { "hunter", 2 } } },
		{ delay = 1000, units = { { "runner", 8 }, { "hunter", 4 }, { "sentinel", 2 } } },
		{ delay = 1100, units = { { "runner", 10 }, { "hunter", 6 }, { "sentinel", 4 } } },
		{ delay = 1200, units = { { "runner", 12 }, { "hunter", 8 }, { "sentinel", 6 } } },
		{ delay = 1300, units = { { "runner", 16 }, { "hunter", 10 }, { "sentinel", 8 } } },
	},

	-- How often, in ticks, the win and lose conditions are checked.
	checkInterval = 25,
}

XenoTypes = { "runner", "hunter", "sentinel", "drone" }
Finished = false
WavesSent = 0

-- Where the waves march. Hunt() cannot be used: it only chases enemies the xeno player can see, and the scripted xeno
-- player has no vision across the map, so the units would stand at the spawn point. Attack-move to the marines' base
-- instead (their units are engaged on the way) and, if the base is gone, to any marine actor.
TargetCell = function()
	for _, kind in ipairs({ "cryo-pod", "vendor", "sentry-turret" }) do
		local found = Marines.GetActorsByType(kind)
		if #found > 0 then
			return found[1].Location
		end
	end
	-- Not GetActors(): that includes the player's own system actor, which has no location.
	local units = Marines.GetActorsByTypes({ "rifleman", "medic", "engineer" })
	if #units > 0 then
		return units[1].Location
	end
	return nil
end

March = function(actor)
	local cell = TargetCell()
	if cell ~= nil and not actor.IsDead then
		actor.AttackMove(cell)
	end
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

SendWave = function(index)
	local wave = Config.waves[index]
	WavesSent = index
	UserInterface.SetMissionText("Wave " .. index .. " of " .. #Config.waves)
	Media.PlaySpeechNotification(Marines, index == #Config.waves and "WaveDistress" or "WaveIncoming")

	for i, unitType in ipairs(Expand(wave.units)) do
		Trigger.AfterDelay(i * 6, function()
			Reinforcements.Reinforce(Xenos, { unitType }, { Utils.Random(Config.spawnCells) }, 0, function(actor)
				March(actor)
				-- Units that arrive and find nothing to fight set off again, towards whatever marine is left.
				Trigger.OnIdle(actor, March)
			end)
		end)
	end

	local nextWave = Config.waves[index + 1]
	if nextWave ~= nil then
		Trigger.AfterDelay(nextWave.delay, function()
			SendWave(index + 1)
		end)
	end
end

Check = function()
	if Finished then
		return
	end

	if Marines.HasNoRequiredUnits() then
		Finished = true
		UserInterface.SetMissionText("The marines have fallen")
		Marines.MarkFailedObjective(Objective)
		return
	end

	if WavesSent == #Config.waves and #Xenos.GetActorsByTypes(XenoTypes) == 0 then
		Finished = true
		UserInterface.SetMissionText("The hive has been beaten back")
		Marines.MarkCompletedObjective(Objective)
		return
	end

	Trigger.AfterDelay(Config.checkInterval, Check)
end

StartWaves = function()
	Marines = Player.GetPlayer("Marines")
	Xenos = Player.GetPlayer("Xenos")
	Objective = Marines.AddPrimaryObjective("Survive " .. #Config.waves .. " waves of xenos")

	UserInterface.SetMissionText("Hold the line")
	Trigger.AfterDelay(Config.waves[1].delay, function()
		SendWave(1)
	end)
	Trigger.AfterDelay(Config.checkInterval, Check)
end

-- A test script can define ConfigOverride(config) and AfterStart(). Scripts load in no fixed order, so they only
-- define these hooks and leave WorldLoaded to this file.
WorldLoaded = function()
	if ConfigOverride ~= nil then
		ConfigOverride(Config)
	end
	StartWaves()
	if AfterStart ~= nil then
		AfterStart()
	end
end
