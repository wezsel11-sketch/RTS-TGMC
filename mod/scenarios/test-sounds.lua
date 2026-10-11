-- Scenario test (see mod/test_scenarios.sh): plays every converted sound, every announcer notification and every music
-- track through the engine, so a missing or undecodable file shows up as a Lua error or a line in sound.log (the harness
-- reads that log). sound-list.lua, written by make_placeholders.py, defines SoundFiles, SpeechNotifications and
-- MusicTracks. The sound engine is a dummy here, so this proves the files load and decode, not how they sound.
-- Prints "TEST sounds PASS" or "TEST sounds FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local played = 0

	for _, file in ipairs(SoundFiles) do
		Media.PlaySound(file)
		played = played + 1
	end
	for _, name in ipairs(SpeechNotifications) do
		Media.PlaySpeechNotification(marines, name)
		played = played + 1
	end

	Trigger.AfterDelay(25, function()
		for _, track in ipairs(MusicTracks) do
			Media.PlayMusic(track)
		end
		Trigger.AfterDelay(25, function()
			print("TEST sounds PASS (" .. played .. " sounds and notifications played, " .. #MusicTracks .. " music tracks started)")
		end)
	end)
end
