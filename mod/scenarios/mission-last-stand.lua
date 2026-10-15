-- Last Stand: a long wave mission on the Hold the Line map. Eight waves that grow every time, and a Behemoth in the last one.
-- The marines lose when their last required unit is gone (see wave-survival.lua).
ConfigOverride = function(config)
	config.spawnCells = { CPos.New(38, 4), CPos.New(38, 9), CPos.New(38, 14), CPos.New(38, 19), CPos.New(38, 24) }
	config.waves =
	{
		{ delay = 600,  units = { { "runner", 6 } } },
		{ delay = 800,  units = { { "runner", 8 }, { "hunter", 2 } } },
		{ delay = 900,  units = { { "runner", 8 }, { "hunter", 4 }, { "spitter", 2 } } },
		{ delay = 1000, units = { { "runner", 10 }, { "hunter", 6 }, { "sentinel", 3 } } },
		{ delay = 1100, units = { { "runner", 12 }, { "hunter", 8 }, { "sentinel", 4 }, { "spitter", 4 } } },
		{ delay = 1200, units = { { "hunter", 10 }, { "sentinel", 6 }, { "spitter", 6 } } },
		{ delay = 1300, units = { { "runner", 14 }, { "hunter", 10 }, { "sentinel", 8 }, { "crusher", 2 } } },
		{ delay = 1400, units = { { "runner", 16 }, { "hunter", 12 }, { "sentinel", 8 }, { "behemoth", 1 } } },
	}
end
