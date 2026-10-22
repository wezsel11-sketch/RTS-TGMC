-- Scenario test: the other orbital warheads and the rail gun (powers of the workshop, see tgmc/rules/structures.yaml).
--   * the rail gun's slug hurts a hunter standing on its spot (it scatters up to four cells, so a pack stands there)
--   * the cluster warhead hurts the hunters in its patch
--   * the incendiary warhead leaves a field of blue fire
-- Prints "TEST orbital-kinds PASS" or "TEST orbital-kinds FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local workshop = marines.GetActorsByType("workshop")[1]
	local xenos = Player.GetPlayer("Xenos")
	local pack = xenos.GetActorsByType("hunter")
	for _, h in ipairs(pack) do
		h.Stance = "HoldFire"
	end

	Trigger.AfterDelay(20, function()
		workshop.ActivateCondorStrike(CPos.New(12, 11), "railgun")
		workshop.ActivateCondorStrike(CPos.New(24, 12), "orbital-cluster")
		workshop.ActivateCondorStrike(CPos.New(15, 20), "orbital-fire")
	end)

	Trigger.AfterDelay(500, function()
		local hurt = 0
		for _, h in ipairs(pack) do
			if h.IsDead or h.Health < h.MaxHealth then
				hurt = hurt + 1
			end
		end
		local fire = #Map.ActorsInCircle(Map.CenterOfCell(CPos.New(15, 20)), WDist.FromCells(9), function(a) return a.Type == "flame-patch-blue" end)
		print("TEST orbital-kinds " .. ((hurt >= 4 and fire >= 20) and "PASS" or "FAIL") .. " (" .. hurt .. " of " .. #pack .. " hunters hurt, " .. fire .. " blue flames)")
	end)
end
