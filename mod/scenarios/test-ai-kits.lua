-- Scenario test: the AI uses the new kinds of ability on its own. A bot squad (squad leader, riflemen, a blademan) meets a bot xeno pack
-- (a bull and runners). Within 40 seconds the bots must have used an aimed ability (a frag), a leader's yell (an aura) and a dash
-- (the blademan's lunge or a bull charge). An ability that is not ready has been used: marines pay no plasma, and the bull starts full.
-- Prints "TEST ai-kits PASS" or "TEST ai-kits FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local aimed, aura, dash = false, false, false
	local function used(actor, slot)
		return not actor.IsDead and actor.AbilityAim(slot) ~= "" and not actor.AbilityReady(slot)
	end
	local function poll()
		for _, r in ipairs(marines.GetActorsByType("rifleman")) do
			if used(r, 1) then aimed = true end
			for _, o in ipairs({ "order-move", "order-hold", "order-focus" }) do
				if not r.IsDead and r.HasAuraCondition(o) then aura = true end
			end
		end
		for _, b in ipairs(marines.GetActorsByType("blademan")) do
			if used(b, 1) then dash = true end
		end
		for _, b in ipairs(xenos.GetActorsByType("bull")) do
			if used(b, 1) or used(b, 2) or used(b, 3) then dash = true end
		end
		if aimed and aura and dash then
			print("TEST ai-kits PASS (aimed, aura, dash)")
			return
		end
		Trigger.AfterDelay(5, poll)
	end
	poll()
	Trigger.AfterDelay(1000, function()
		print("TEST ai-kits FAIL (aimed " .. tostring(aimed) .. ", aura " .. tostring(aura) .. ", dash " .. tostring(dash) .. ")")
	end)
end
