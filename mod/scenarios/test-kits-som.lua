-- Scenario test: every SOM unit has at least one ability, and every ability it has can be used:
-- self/nearest/forward ones with UseAbility, spot-aimed ones on a xeno's cell, unit-aimed ones on a xeno or on a hurt marine. A toggle
-- of a group that is already on counts as used. Xenos hold fire and are tough so nothing dies early.
-- Prints "TEST kits-som PASS" or "TEST kits-som FAIL (unit:slot ...)".
Types = { "som_trooper", "som_veteran", "som_corpsman", "som_engineer", "som_squad_leader", "som_field_commander", "som_smartgunner",
	"som_flamer", "som_grenadier", "som_machinegunner", "som_blademan", "som_scout", "som_mortarman", "som_heavygunner", "som_rocketeer",
	"som_demolitionist", "som_assault", "som_bomber", "som_mech" }

-- Uses one slot the way its aim needs; true if it went off (or is a toggle already on).
UseSlot = function(unit, slot, foe, friend)
	local aim = unit.AbilityAim(slot)
	if aim == "" then return nil end
	if unit.AbilityActive(slot) then return true end
	if aim == "Target" then return unit.UseAbilityAt(slot, foe.Location) end
	if aim == "TargetActor" then return unit.UseAbilityOn(slot, foe) or unit.UseAbilityOn(slot, friend) end
	return unit.UseAbility(slot) or unit.AbilityActive(slot)
end

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local foes = Player.GetPlayer("Xenos").GetActorsByType("runner")
	Utils.Do(foes, function(f) f.Stance = "HoldFire" end)
	local friend = marines.GetActorsByType("cryo-pod")[1]
	local bad = {}
	Trigger.AfterDelay(15, function()
		for _, t in ipairs(Types) do
			local unit = marines.GetActorsByType(t)[1]
			if unit == nil then
				bad[#bad + 1] = t .. ":missing"
			else
				pcall(function() unit.Stance = "HoldFire" end)
				local foe = Utils.Where(foes, function(f) return not f.IsDead end)[1]
				local count = 0
				for slot = 1, 8 do
					local ok, used = pcall(UseSlot, unit, slot, foe, friend)
					if ok and used ~= nil then
						count = count + 1
						if not used then bad[#bad + 1] = t .. ":" .. slot end
					end
				end
				if count == 0 then bad[#bad + 1] = t .. ":none" end
			end
		end
		print("TEST kits-som " .. (#bad == 0 and "PASS" or ("FAIL (" .. table.concat(bad, " ") .. ")")))
	end)
end
