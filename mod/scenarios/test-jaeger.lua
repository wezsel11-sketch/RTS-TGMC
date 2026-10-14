-- Scenario test: the Jaeger-armoured marines (scout, skirmisher, trooper, ranger, assault) each hurt a crusher standing three cells away, and
-- the armour classes order their health. Prints "TEST jaeger PASS" or "TEST jaeger FAIL".
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local types = { "scout", "skirmisher", "trooper", "ranger", "assault" }
	local targets = xenos.GetActorsByType("crusher")
	local start = {}
	for i, t in ipairs(targets) do
		start[i] = t.Health
		t.Stance = "HoldFire"
	end
	local hp = {}
	for _, a in ipairs(marines.GetActorsByTypes(types)) do
		hp[a.Type] = a.MaxHealth
	end
	Trigger.AfterDelay(400, function()
		local hurt = 0
		for i, t in ipairs(targets) do
			if t.IsDead or t.Health < start[i] then
				hurt = hurt + 1
			end
		end
		local ordered = hp["scout"] < hp["skirmisher"] and hp["skirmisher"] < hp["ranger"] and hp["ranger"] < hp["trooper"] and hp["trooper"] < hp["assault"]
		print("TEST jaeger " .. ((hurt == #types and ordered) and "PASS" or "FAIL") .. " (" .. hurt .. " of " .. #types .. " targets hurt, health ordered=" .. tostring(ordered) .. ")")
	end)
end
