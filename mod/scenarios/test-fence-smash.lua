-- Scenario test: the heavy castes walk through fences and break them. A fence runs down the whole map at x 14. A crusher and a hunter are
-- both sent across: the crusher must arrive and leave a hole, the hunter must still be on its own side. Prints "TEST fence-smash PASS" or "... FAIL".
local fences = function()
	return #Utils.Where(Map.ActorsInWorld, function(a) return a.Owner.InternalName == "Neutral" end)
end

WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local crusher = xenos.GetActorsByType("crusher")[1]
	local hunter = xenos.GetActorsByType("hunter")[1]
	local before = fences()
	crusher.Move(CPos.New(22, 8))
	hunter.Move(CPos.New(22, 14))
	Trigger.AfterDelay(700, function()
		local ok = crusher.Location.X >= 20 and hunter.Location.X < 14 and fences() < before
		print("TEST fence-smash " .. (ok and "PASS" or "FAIL") .. " (crusher at x " .. crusher.Location.X .. ", hunter at x " .. hunter.Location.X .. ", fences "
			.. before .. " then " .. fences() .. ")")
	end)
end
