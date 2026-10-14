-- Scenario test: the defiler's canister leaves a gas cloud that hurts and slows the marine standing in it.
-- Prints "TEST gas PASS" or "TEST gas FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local target = marines.GetActorsByType("rifleman")[1]
	local h0 = target.Health
	local clouds = 0
	xenos.GetActorsByType("defiler")[1].Attack(target, true, true)

	local function poll(ticks)
		clouds = math.max(clouds, #xenos.GetActorsByType("gas-cloud"))
		if ticks >= 500 then
			print("TEST gas " .. ((target.IsDead or target.Health < h0) and clouds > 0 and "PASS" or "FAIL") .. " (marine " .. h0 .. " -> " .. (target.IsDead and 0 or target.Health) .. ", most clouds " .. clouds .. ")")
		else
			Trigger.AfterDelay(10, function() poll(ticks + 10) end)
		end
	end
	Trigger.AfterDelay(10, function() poll(10) end)
end
