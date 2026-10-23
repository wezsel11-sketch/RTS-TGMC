-- Scenario test (see mod/test_scenarios.sh): the tech tree and the supply generators of the building system.
--   * the marine and xeno tech structures are not prerequisites until they exist, then they are (so the gated units unlock)
--   * a Miner and a Weed Node each add requisition on top of the starting base's trickle
-- Placing from the Build tab goes through the sidebar and engine orders, which a script cannot drive, so that part is checked
-- by hand (see README). Prints "TEST build PASS" or "TEST build FAIL".
local reported = false

local function fail(why)
	if not reported then
		reported = true
		print("TEST build FAIL (" .. why .. ")")
	end
end

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	-- The engineer's shotgun would shoot the Weed Node this test counts the income of.
	marines.GetActorsByType("engineer")[1].Stance = "HoldFire"

	Trigger.AfterDelay(10, function()
		if marines.HasPrerequisites({ "armory" }) or marines.HasPrerequisites({ "ordnance-depot" }) then
			return fail("marine tech should be locked at the start")
		end
		if xenos.HasPrerequisites({ "evolution-tower" }) or xenos.HasPrerequisites({ "maturity-tower" }) then
			return fail("xeno tech should be locked at the start")
		end
		if not xenos.HasPrerequisites({ "queen" }) or not xenos.HasPrerequisites({ "resin-silo" }) then
			return fail("the starting queen and silo should be prerequisites")
		end

		Actor.Create("armory", true, { Owner = marines, Location = CPos.New(12, 8) })
		Actor.Create("ordnance-depot", true, { Owner = marines, Location = CPos.New(14, 8) })
		Actor.Create("evolution-tower", true, { Owner = xenos, Location = CPos.New(14, 4) })
		Actor.Create("maturity-tower", true, { Owner = xenos, Location = CPos.New(18, 4) })
		Actor.Create("miner", true, { Owner = marines, Location = CPos.New(12, 12) })
		Actor.Create("weed-node", true, { Owner = xenos, Location = CPos.New(14, 10) })
		local marineCash, xenoCash = marines.Cash, xenos.Cash

		Trigger.AfterDelay(20, function()
			if not (marines.HasPrerequisites({ "armory" }) and marines.HasPrerequisites({ "ordnance-depot" })) then
				return fail("marine tech should unlock once built")
			end
			if not (xenos.HasPrerequisites({ "evolution-tower" }) and xenos.HasPrerequisites({ "maturity-tower" })) then
				return fail("xeno tech should unlock once built")
			end
		end)

		Trigger.AfterDelay(230, function()
			if reported then
				return
			end
			-- The marine base has no income of its own, so any gain is the Miner (8 every 50 ticks).
			local marineGain, xenoGain = marines.Cash - marineCash, xenos.Cash - xenoCash
			if marineGain < 16 then
				return fail("the Miner added only " .. marineGain)
			end
			-- The silo alone gives at most 6 x 5 in this time; with the Weed Node's 7 per 50 ticks it is well over 40.
			if xenoGain < 40 then
				return fail("the silo and Weed Node added only " .. xenoGain)
			end
			reported = true
			print("TEST build PASS (marines +" .. marineGain .. ", xenos +" .. xenoGain .. ")")
		end)
	end)
end
