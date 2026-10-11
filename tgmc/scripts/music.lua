-- Faction-aware music for every map. OpenRA's own playlist cannot filter by faction, so this script plays the tracks in
-- audio/music.yaml itself with Media.PlayMusic and chains one to the next. It only changes what the local player hears.
--
--  * Marines get the hopeful themes, the elevator and lobby tracks and the station ambience; xenos get the melancholy
--    themes, the dread theme and the cave, lava and jungle ambience. An observer gets a bit of both.
--  * A theme and an ambience track alternate, so the many ambience loops do not bury the themes.
--  * When an enemy comes near one of your units or structures the tense tracks take over, and they stay for a while
--    after the fight. The in-game next/previous keys still work; after one, the engine's own shuffled playlist continues.
--
-- A map that has its own script lists this one last, and it wraps that script's WorldLoaded (see the end of the file).

TGMCMusic = {}

TGMCMusic.Pools =
{
	marines =
	{
		themes = { "theme-hopeful-1", "theme-hopeful-2", "theme-lobby", "theme-elevator" },
		calm =
		{
			"ambient-station-1", "ambient-station-2", "ambient-station-3", "ambient-station-4", "ambient-station-5",
			"ambient-station-6", "ambient-station-7", "ambient-station-8", "ambient-station-9", "ambient-station-10",
			"ambient-station-11", "ambient-station-12", "ambient-station-13", "ambient-station-14",
			"ambient-tech-1", "ambient-tech-2", "ambient-ship", "ambient-signal-1", "ambient-signal-2",
			"ambient-signal-3", "ambient-signal-4", "ambient-chapel-1", "ambient-chapel-2", "ambient-chapel-3",
			"ambient-chapel-4"
		},
		combat = { "theme-tense-1", "theme-tense-2" },
	},
	xenos =
	{
		themes = { "theme-melancholy-1", "theme-melancholy-2", "theme-dread" },
		calm =
		{
			"ambient-cave", "ambient-lava-1", "ambient-lava-2", "ambient-lava-3", "ambient-mine", "ambient-malf",
			"ambient-jungle", "ambient-wind", "ambient-moon-1", "ambient-moon-2", "ambient-space", "ambient-atmos-1",
			"ambient-atmos-2", "ambient-atmos-3"
		},
		combat = { "theme-tense-1", "theme-tense-2", "theme-dread" },
	},
}

TGMCMusic.Config =
{
	-- Ticks between looks for enemies near the local player's units (a tick is 40 ms).
	pollInterval = 60,
	-- Own actors checked per look, and how close an enemy has to be, in cells.
	sample = 12,
	threatRange = 8,
	-- Ticks without a threat before the fight counts as over, and the fewest ticks between two switches of mood.
	calmAfter = 750,
	minSwitch = 500,
	-- Ticks to wait before the first track, so that it replaces the one the engine starts when the world finishes loading.
	startDelay = 10,
}

TGMCMusic.State = { pool = nil, inCombat = false, lastThreat = -100000, lastSwitch = -100000, generation = 0, turn = 0, queues = {} }

-- Park-Miller generator: math.random is not available to scripts, and this only has to be good enough to shuffle music
TGMCMusic.Rand = function(low, high)
	local state = (TGMCMusic.State.seed * 16807) % 2147483647
	TGMCMusic.State.seed = state
	return low + state % (high - low + 1)
end

TGMCMusic.Shuffled = function(list)
	local copy = {}
	for i, v in ipairs(list) do copy[i] = v end
	for i = #copy, 2, -1 do
		local j = TGMCMusic.Rand(1, i)
		copy[i], copy[j] = copy[j], copy[i]
	end
	return copy
end

-- The next track of a list, walking a shuffled copy of it and shuffling again when it runs out.
TGMCMusic.Draw = function(name, list)
	local queue = TGMCMusic.State.queues[name]
	if queue == nil or #queue == 0 then
		queue = TGMCMusic.Shuffled(list)
		TGMCMusic.State.queues[name] = queue
	end
	return table.remove(queue)
end

TGMCMusic.NextTrack = function()
	local pool = TGMCMusic.State.pool
	if TGMCMusic.State.inCombat then
		return TGMCMusic.Draw("combat", pool.combat)
	end
	TGMCMusic.State.turn = TGMCMusic.State.turn + 1
	if TGMCMusic.State.turn % 2 == 1 then
		return TGMCMusic.Draw("themes", pool.themes)
	end
	return TGMCMusic.Draw("calm", pool.calm)
end

TGMCMusic.PlayNext = function()
	TGMCMusic.State.generation = TGMCMusic.State.generation + 1
	local generation = TGMCMusic.State.generation
	Media.PlayMusic(TGMCMusic.NextTrack(), function()
		-- A newer track replaced this one; its own callback carries on the chain
		if generation == TGMCMusic.State.generation then
			TGMCMusic.PlayNext()
		end
	end)
end

TGMCMusic.LocalPlayer = function()
	local found = Player.GetPlayers(function(p) return p.IsLocalPlayer end)
	return found[1]
end

-- True when an enemy of the local player stands within threatRange cells of one of its actors.
TGMCMusic.EnemyNearby = function(me)
	local own = me.GetActors()
	if #own == 0 then
		return false
	end
	local range = WDist.FromCells(TGMCMusic.Config.threatRange)
	local checked = math.min(TGMCMusic.Config.sample, #own)
	local start = TGMCMusic.Rand(1, #own)
	for n = 0, checked - 1 do
		local actor = own[(start + n) % #own + 1]
		local near = Map.ActorsInCircle(actor.CenterPosition, range, function(a)
			return not a.IsDead and a.Owner ~= nil and not a.Owner.IsNonCombatant and a.Owner.Faction ~= me.Faction
		end)
		if #near > 0 then
			return true
		end
	end
	return false
end

TGMCMusic.Poll = function(me)
	local now = DateTime.GameTime
	local ok, threat = pcall(TGMCMusic.EnemyNearby, me)
	if ok and threat then
		TGMCMusic.State.lastThreat = now
	end

	local wantCombat = now - TGMCMusic.State.lastThreat < TGMCMusic.Config.calmAfter
	if wantCombat and not TGMCMusic.State.inCombat and now - TGMCMusic.State.lastSwitch >= TGMCMusic.Config.minSwitch then
		TGMCMusic.State.inCombat = true
		TGMCMusic.State.lastSwitch = now
		TGMCMusic.PlayNext() -- cut the calm track off for the tense one
	elseif not wantCombat and TGMCMusic.State.inCombat then
		-- Let the tense track finish; the next pick is a calm one
		TGMCMusic.State.inCombat = false
		TGMCMusic.State.lastSwitch = now
	end

	Trigger.AfterDelay(TGMCMusic.Config.pollInterval, function() TGMCMusic.Poll(me) end)
end

TGMCMusic.StartMusic = function()
	-- Utils.RandomInteger is the one random source that is safe in a script; the rest is a private generator
	TGMCMusic.State.seed = Utils.RandomInteger(1, 2147483646)
	local me = TGMCMusic.LocalPlayer()
	if me ~= nil and TGMCMusic.Pools[me.Faction] ~= nil then
		TGMCMusic.State.pool = TGMCMusic.Pools[me.Faction]
	else
		-- An observer, or a faction without its own pool: a bit of both
		TGMCMusic.State.pool =
		{
			themes = { "theme-hopeful-1", "theme-melancholy-1", "theme-hopeful-2", "theme-melancholy-2", "theme-lobby" },
			calm = TGMCMusic.Pools.marines.calm,
			combat = { "theme-tense-1", "theme-tense-2", "theme-dread" },
		}
		me = nil
	end

	Trigger.AfterDelay(TGMCMusic.Config.startDelay, function()
		TGMCMusic.PlayNext()
		if me ~= nil then
			Trigger.AfterDelay(TGMCMusic.Config.pollInterval, function() TGMCMusic.Poll(me) end)
		end
	end)
end

-- Run after whatever WorldLoaded the map's own script defined, if any
TGMCMusic.MapWorldLoaded = WorldLoaded
WorldLoaded = function()
	if TGMCMusic.MapWorldLoaded ~= nil then
		TGMCMusic.MapWorldLoaded()
	end
	TGMCMusic.StartMusic()
end
