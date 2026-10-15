-- Night Raid: a wave mission on the Hold the Line map. The xenos come in from both the north-east and the south-east edge,
-- with spitters that shoot from range, and a drone that walks ahead to plant weeds. Uses wave-survival.lua for the waves.
ConfigOverride = function(config)
	config.spawnCells = { CPos.New(38, 3), CPos.New(38, 6), CPos.New(38, 21), CPos.New(38, 25) }
	config.waves =
	{
		{ delay = 600,  units = { { "runner", 8 } } },
		{ delay = 800,  units = { { "runner", 8 }, { "spitter", 3 } } },
		{ delay = 900,  units = { { "runner", 10 }, { "hunter", 4 }, { "spitter", 4 } } },
		{ delay = 1000, units = { { "runner", 12 }, { "hunter", 6 }, { "spitter", 6 }, { "drone", 1 } } },
		{ delay = 1100, units = { { "hunter", 8 }, { "sentinel", 4 }, { "spitter", 6 }, { "drone", 1 } } },
	}
end
