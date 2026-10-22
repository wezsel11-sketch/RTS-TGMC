-- Scenario test: the caste abilities of the command card. Rage works once and then recovers; the praetorian's acid spray hurts a marine in front
-- of him and leaves acid gas; the wraith blinks next to the nearest marine; the defiler fills the ground around him with gas while he walks; the warrior's fling throws the marine next to him; the carrier throws huggers until its charges run out.
-- Prints "TEST abilities PASS" or "TEST abilities FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local marines = Player.GetPlayer("Marines")
	for _, m in ipairs(marines.GetActorsByType("rifleman")) do
		m.Stance = "HoldFire"
	end
	local ravager = xenos.GetActorsByType("ravager")[1]
	local praetorian = xenos.GetActorsByType("praetorian")[1]
	local warrior = xenos.GetActorsByType("warrior")[1]
	local carrier = xenos.GetActorsByType("carrier")[1]
	local wraith = xenos.GetActorsByType("wraith")[1]
	local blinkTarget
	local defiler = xenos.GetActorsByType("defiler")[1]
	local sprayTarget, flingTarget
	for _, m in ipairs(marines.GetActorsByType("rifleman")) do
		if m.Location.Y == 10 then
			sprayTarget = m
		elseif m.Location.Y == 16 then
			flingTarget = m
		elseif m.Location.Y == 20 then
			blinkTarget = m
		end
	end
	local sprayHp, flingX = sprayTarget.Health, flingTarget.Location.X
	local results = {}
	local gas, puffs = 0, 0

	Trigger.AfterDelay(10, function()
		results.rage1 = ravager.UseAbility(1)
		results.rage2 = ravager.UseAbility(1)
		results.spray = praetorian.UseAbility(1)
		results.fling = warrior.UseAbility(1)
		results.blink = wraith.UseAbility(2)
		results.emit = defiler.UseAbility(1)
		defiler.Move(CPos.New(defiler.Location.X + 10, defiler.Location.Y))
		-- Counted while the gas still hangs: the defiler fills the cells around him as he walks.
		Trigger.AfterDelay(90, function() puffs = #xenos.GetActorsByType("gas-cloud") end)
		-- The acid gas lasts eight seconds, so count it soon after the spray.
		Trigger.AfterDelay(30, function() gas = #xenos.GetActorsByType("acid-gas") end)
		local uses = 0
		for i = 0, 5 do
			Trigger.AfterDelay(i * 50, function()
				if carrier.UseAbility(1) then
					uses = uses + 1
				end
			end)
		end
		Trigger.AfterDelay(400, function()
			local huggers = #xenos.GetActorsByType("facehugger")
			local sprayed = sprayTarget.IsDead or sprayTarget.Health < sprayHp
			local flung = not flingTarget.IsDead and flingTarget.Location.X >= flingX + 3
			local blinked = math.abs(wraith.Location.X - blinkTarget.Location.X) <= 2 and math.abs(wraith.Location.Y - blinkTarget.Location.Y) <= 2
			local ok = results.rage1 and not results.rage2 and results.spray and results.fling and sprayed and flung and uses == 4 and gas >= 5 and results.blink and blinked and results.emit and puffs >= 20
			print("TEST abilities " .. (ok and "PASS" or "FAIL") .. " (rage " .. tostring(results.rage1) .. "/" .. tostring(results.rage2) ..
				", sprayed=" .. tostring(sprayed) .. ", acid gas " .. gas .. ", defiler gas " .. puffs .. ", blinked=" .. tostring(blinked) .. ", flung=" .. tostring(flung) .. ", huggers thrown " .. uses .. ", huggers " .. huggers .. ")")
		end)
	end)
end
