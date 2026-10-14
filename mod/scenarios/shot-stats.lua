-- Not a test: wins the game for the marines early so the end-of-match table can be photographed.
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	Trigger.AfterDelay(50, function()
		Utils.Do(xenos.GetActorsByTypes({ "runner", "mini-silo" }), function(a)
			a.Kill()
		end)
	end)
end
