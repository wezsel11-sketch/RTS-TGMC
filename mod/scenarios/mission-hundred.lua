-- The Hundred: a hundred waves on the Hold the Line map, generated from one formula. The waves grow, the xeno kinds rise from runners
-- to behemoths, and every tenth wave from 25 on brings a behemoth. Clear the hundredth wave to win.
ConfigOverride = function(config)
	config.spawnCells = { CPos.New(38, 4), CPos.New(38, 9), CPos.New(38, 14), CPos.New(38, 19), CPos.New(38, 24) }
	local waves = {}
	for i = 1, 100 do
		local units = { { "runner", 3 + math.floor(i * 0.5) } }
		if i >= 3 then
			table.insert(units, { "hunter", math.floor(i * 0.3) })
		end
		if i >= 5 then
			table.insert(units, { "spitter", math.floor(i * 0.2) })
		end
		if i >= 8 then
			table.insert(units, { "sentinel", math.floor(i * 0.2) })
		end
		if i >= 20 then
			table.insert(units, { "crusher", math.floor(i * 0.1) })
		end
		if i >= 30 then
			table.insert(units, { "ravager", math.floor(i * 0.1) })
		end
		if i >= 40 then
			table.insert(units, { "warlock", math.floor(i * 0.08) })
		end
		if i >= 25 and i % 10 == 0 then
			table.insert(units, { "behemoth", 1 + math.floor(i / 50) })
		end
		waves[i] = { delay = math.max(450, 900 - i * 4), units = units }
	end
	config.waves = waves
end
