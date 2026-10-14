-- Scenario test: a larva evolves into a runner for the price difference, then devolves back and is refunded part of it.
-- Prints "TEST evolve PASS" or "TEST evolve FAIL".
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	xenos.Cash = 500
	local larva = xenos.GetActorsByType("larva")[1]
	larva.Evolve()

	Trigger.AfterDelay(75, function()
		local runners = xenos.GetActorsByType("runner")
		local larvae = #xenos.GetActorsByType("larva")
		local paid = 500 - xenos.Cash
		if #runners ~= 1 or larvae ~= 0 then
			print("TEST evolve FAIL (runners=" .. #runners .. ", larvae=" .. larvae .. ")")
			return
		end
		print("TEST evolve note: evolved, paid " .. paid)
		runners[1].Devolve()
		Trigger.AfterDelay(75, function()
			local ok = #xenos.GetActorsByType("larva") == 1 and #xenos.GetActorsByType("runner") == 0
			print("TEST evolve " .. (ok and "PASS" or "FAIL") .. " (back to larva=" .. tostring(ok) .. ", cash " .. xenos.Cash .. ")")
		end)
	end)
end
