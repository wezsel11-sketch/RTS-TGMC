-- Scenario test: explosives hurt friendly units (friendly fire), and the B17 demolitionist's armour turns most of a blast
-- aside. A demolitionist fires at a xeno standing between a rifleman and a second demolitionist; both stand a cell from it.
-- Prints "TEST explosive PASS" or "TEST explosive FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local target = xenos.GetActorsByType("crusher")[1]
	target.Stance = "HoldFire"
	local shooter, bystander
	for _, d in ipairs(marines.GetActorsByType("demolitionist")) do
		if d.Location.X == 10 then
			shooter = d
		else
			bystander = d
		end
	end
	local rifleman = marines.GetActorsByType("rifleman")[1]
	rifleman.Stance = "HoldFire"
	bystander.Stance = "HoldFire"
	local rifleMax, demoMax = rifleman.MaxHealth, bystander.MaxHealth
	local function lost(a, max)
		if a.IsDead then
			return max
		end
		return max - a.Health
	end

	Trigger.AfterDelay(25, function()
		shooter.Attack(target)
	end)

	Trigger.AfterDelay(150, function()
		local rifleLoss = lost(rifleman, rifleMax)
		local demoLoss = lost(bystander, demoMax)
		-- Friendly fire hit the rifleman, and the B17 lost far less of its health than he did.
		-- Compare shares of health lost, since the B17 has more health than a rifleman.
		local ok = rifleLoss > 0 and (demoLoss / demoMax) * 2 < (rifleLoss / rifleMax)
		print("TEST explosive " .. (ok and "PASS" or "FAIL") .. " (rifleman lost " .. rifleLoss .. ", B17 lost " .. demoLoss .. ")")
	end)
end
