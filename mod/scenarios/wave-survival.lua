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
		{ delay = 750,  units = { { "runner", 4 } } },
		{ delay = 900,  units = { { "runner", 6 } } },
		{ delay = 1100, units = { { "runner", 4 }, { "hunter", 2 } } },
		{ delay = 1200, units = { { "runner", 6 }, { "hunter", 3 }, { "sentinel", 1 } } },
		{ delay = 1300, units = { { "runner", 6 }, { "hunter", 4 }, { "sentinel", 3 } } },
		{ delay = 1400, units = { { "runner", 8 }, { "hunter", 5 }, { "sentinel", 4 } } },
	},

	-- How often, in ticks, the win and lose conditions are checked.
	checkInterval = 25,
}

XenoTypes = { "runner", "hunter", "sentinel", "drone" }
Finished = false
WavesSent = 0

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

	for i, unitType in ipairs(Expand(wave.units)) do
		Trigger.AfterDelay(i * 6, function()
			Reinforcements.Reinforce(Xenos, { unitType }, { Utils.Random(Config.spawnCells) }, 0, function(actor)
				actor.Hunt()
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
