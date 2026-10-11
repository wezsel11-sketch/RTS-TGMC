-- Scenario test (see mod/test_scenarios.sh): heavy armour shrugs off rifle fire. A rifleman shoots an idle Crusher and
-- another shoots an idle Hunter, both four cells away. The Hunter should lose most of its health, the Crusher very little,
-- and a mech's cannon should hurt a Crusher far more than the rifle did.
-- Prints "TEST armor PASS" or "TEST armor FAIL" with what each target lost.
local function at(player, type, x, y)
	for _, a in ipairs(player.GetActorsByType(type)) do
		if a.Location.X == x and a.Location.Y == y then
			return a
		end
	end
end

WorldLoaded = function()
	local marines, xenos = Player.GetPlayer("Marines"), Player.GetPlayer("Xenos")
	local crusher, hunter = at(xenos, "crusher", 8, 3), at(xenos, "hunter", 8, 10)
	local crusher2 = at(xenos, "crusher", 28, 3)
	local maxHealth = {}
	for _, a in ipairs({ crusher, hunter, crusher2 }) do
		a.Stance = "HoldFire"
		maxHealth[a] = a.MaxHealth
	end

	Trigger.AfterDelay(150, function()
		local lost = function(a) return a.IsDead and maxHealth[a] or (maxHealth[a] - a.Health) end
		local cl, hl, ml = lost(crusher), lost(hunter), lost(crusher2)
		local ok = cl > 0 and cl <= 70 and hl >= 80 and ml >= 2 * cl
		print("TEST armor " .. (ok and "PASS" or "FAIL") .. " (rifle: Crusher lost " .. cl .. " of " .. maxHealth[crusher] .. ", Hunter lost " .. hl
			.. " of " .. maxHealth[hunter] .. "; mech: Crusher lost " .. ml .. ")")
	end)
end
