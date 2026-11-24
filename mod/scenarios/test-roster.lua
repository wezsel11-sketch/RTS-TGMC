-- Scenario test: the rosters. With every tech building standing, the human side (marines in scenario-roster, SOM in
-- scenario-roster-som) can build exactly its fourteen infantry-tab units and its vehicles on the Vehicle tab. The cut units and
-- the other side's units must not be on the list. Prints "TEST roster PASS" or "TEST roster FAIL".
local want = {
	marines = {
		Infantry = "engineer,field_commander,flamer,grenadier,machinegunner,medic,rifleman,rocketeer,smartgunner,sniper,squad_leader,synth",
		Vehicle = "apc,mech,tank",
	},
	som = {
		Infantry = "som_blademan,som_breacher,som_caliver,som_corpsman,som_engineer,som_flamer,som_heavygunner,som_machinegunner," ..
			"som_pointman,som_rocketeer,som_scout,som_squad_leader,som_trooper,som_veteran",
		Vehicle = "som_mech,som-tank",
	},
}

WorldLoaded = function()
	local player = Player.GetPlayer("Marines")
	Trigger.AfterDelay(50, function()
		local w = want[player.Faction]
		local infantry, vehicle = player.BuildList("Infantry"), player.BuildList("Vehicle")
		local ok = w and infantry == w.Infantry and vehicle == w.Vehicle
		print("TEST roster " .. (ok and "PASS" or "FAIL") .. " (" .. player.Faction .. " infantry " .. infantry .. "; vehicles " .. vehicle .. ")")
	end)
end
