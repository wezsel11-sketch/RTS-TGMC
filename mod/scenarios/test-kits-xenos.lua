-- Scenario test: every xeno caste has at least one ability, and every ability it has can be used:
-- self/nearest/forward ones with UseAbility, spot-aimed ones on a marine's cell, unit-aimed ones on a marine or on a hurt xeno. A toggle
-- of a group that is already on counts as used. Marines hold fire and are tough; every xeno starts with full plasma so nothing dies early.
-- Prints "TEST kits-xenos PASS" or "TEST kits-xenos FAIL (unit:slot ...)".
Types = { "runner", "hunter", "sentinel", "facehugger", "drone", "warrior", "queen", "spitter", "praetorian", "crusher", "ravager", "defiler",
	"boiler", "carrier", "warlock", "shrike", "widow", "wraith", "bull", "behemoth" }

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
	local own = Player.GetPlayer("Xenos")
	local foes = Player.GetPlayer("Marines").GetActorsByType("rifleman")
	Utils.Do(foes, function(f) f.Stance = "HoldFire" end)
	-- A hurt xeno for the heals to work on.
	local friend = own.GetActorsByType("larva")[1]
	friend.Health = math.floor(friend.MaxHealth / 3)
	local bad = {}
	-- One caste at a time: a marine is moved next to it (melee abilities need one at arm's length), and two ticks later, once the
	-- move has happened, every ability it has is tried.
	for i, t in ipairs(Types) do
		Trigger.AfterDelay(10 + i * 4, function()
			local unit = own.GetActorsByType(t)[1]
			if unit == nil then
				bad[#bad + 1] = t .. ":missing"
				return
			end
			pcall(function() unit.Stance = "HoldFire" end)
			-- Each caste gets the next marine, so one a facehugger latched on to is not reused at once.
			local alive = Utils.Where(foes, function(f) return not f.IsDead end)
			local foe = alive[(i % #alive) + 1]
			foe.Teleport(unit.Location + CVec.New(1, 0))
			Trigger.AfterDelay(2, function()
				local count = 0
				for slot = 1, 8 do
					local ok, used = pcall(UseSlot, unit, slot, foe, friend)
					if ok and used ~= nil then
						count = count + 1
						if not used then bad[#bad + 1] = t .. ":" .. slot end
					end
				end
				if count == 0 then bad[#bad + 1] = t .. ":none" end
			end)
		end)
	end
	-- The boiler's bombard with the neuro glob loaded: the slot's other (switched-off) bombard must not be the one used.
	Trigger.AfterDelay(14 + #Types * 4, function()
		local boiler = own.GetActorsByType("boiler")[1]
		boiler.UseAbility(3)
		Trigger.AfterDelay(2, function()
			if not boiler.UseAbilityAt(1, foes[1].Location) then bad[#bad + 1] = "boiler:neuro-bombard" end
		end)
	end)
	Trigger.AfterDelay(20 + #Types * 4, function()
		print("TEST kits-xenos " .. (#bad == 0 and "PASS" or ("FAIL (" .. table.concat(bad, " ") .. ")")))
	end)
end
