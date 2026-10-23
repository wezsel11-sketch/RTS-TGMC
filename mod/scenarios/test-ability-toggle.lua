-- Scenario test: shell-type toggles. A mortarman has HE (slot 1, on at the start) and Smoke (slot 2) in one group: picking Smoke turns
-- HE off, and picking Smoke again keeps it on (one shell type is always loaded, never two).
-- Prints "TEST ability-toggle PASS" or "TEST ability-toggle FAIL".
WorldLoaded = function()
	local mortar = Player.GetPlayer("Marines").GetActorsByType("mortarman")[1]
	mortar.Stance = "HoldFire"
	local steps = {}
	local function state() return tostring(mortar.AbilityActive(1)) .. "/" .. tostring(mortar.AbilityActive(2)) end
	Trigger.AfterDelay(5, function() steps[1] = state() end)
	Trigger.AfterDelay(10, function() mortar.UseAbility(2) steps[2] = state() end)
	Trigger.AfterDelay(20, function()
		mortar.UseAbility(2)
		steps[3] = state()
		local ok = steps[1] == "true/false" and steps[2] == "false/true" and steps[3] == "false/true"
		print("TEST ability-toggle " .. (ok and "PASS" or "FAIL") .. " (" .. table.concat(steps, ", ") .. ")")
	end)
end
