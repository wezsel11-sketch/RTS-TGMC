-- Scenario test: autocast. A rifleman faces three hunters, everyone holding fire, so only its frag (slot 1) can hurt them. With autocast off
-- it throws nothing; switched on, it throws by itself. Prints "TEST ability-autocast PASS" or "TEST ability-autocast FAIL".
WorldLoaded = function()
	local rifleman = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	local hunters = Player.GetPlayer("Xenos").GetActorsByType("hunter")
	rifleman.Stance = "HoldFire"
	-- Stealth off: autocast, like the AI, only aims at what it can see.
	Utils.Do(hunters, function(h)
		h.Stance = "HoldFire"
		h.UseAbility(1)
	end)

	local function hurt()
		local n = 0
		for _, h in ipairs(hunters) do
			if h.IsDead or h.Health < h.MaxHealth then
				n = n + 1
			end
		end
		return n
	end

	Trigger.AfterDelay(150, function()
		if hurt() > 0 then
			print("TEST ability-autocast FAIL (a hunter was hurt before autocast was on)")
			return
		end

		rifleman.AbilityAutoCast(1, true)
		if not rifleman.AbilityAutoCasting(1) then
			print("TEST ability-autocast FAIL (autocast did not switch on)")
			return
		end

		Trigger.AfterDelay(150, function()
			if hurt() > 0 then
				print("TEST ability-autocast PASS (" .. hurt() .. " hunters hit)")
			else
				print("TEST ability-autocast FAIL (no frag with autocast on)")
			end
		end)
	end)
end
