-- Scenario test: a facehugger latches onto a marine, a corpsman cures them at full health, unordered, before the burst, and nothing bursts.
-- Prints "TEST autocure PASS" or "TEST autocure FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local host = nil
	for _, a in ipairs(marines.GetActorsByType("rifleman")) do
		if a.Location.X == 10 then
			host = a
		end
	end
	host.Stance = "HoldFire"

	Trigger.AfterDelay(500, function()
		local larvae = #xenos.GetActorsByType("larva")
		local ok = (not host.IsDead) and larvae == 0
		print("TEST autocure " .. (ok and "PASS" or "FAIL") .. " (host dead=" .. tostring(host.IsDead) .. ", larvae=" .. larvae .. ")")
	end)
end
