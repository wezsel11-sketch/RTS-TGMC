-- Not a test: the ground effects in one view (GroundFx.cs). Ash storm weather (map rules); riflemen and a machine gunner fire at a
-- resin turret (bullet holes, the gun's heat bar); a spitter spits at a cade (acid holes); a hurt marine and a hurt runner walk
-- (bloody footprints); a drop pod and an orbital strike are called in (blinking ground markers).
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local turret = xenos.GetActorsByType("resin-turret")[1]
	local cade = marines.GetActorsByType("cade")[1]
	turret.Stance = "HoldFire"
	Trigger.AfterDelay(10, function()
		for _, t in ipairs({ "rifleman", "machinegunner" }) do
			for _, a in ipairs(marines.GetActorsByType(t)) do
				if a.Location.Y < 10 then a.Attack(turret, true, true) end
			end
		end
		xenos.GetActorsByType("spitter")[1].Attack(cade, true, true)
		for _, a in ipairs(marines.GetActorsByType("rifleman")) do
			if a.Location.Y >= 14 then
				a.Health = math.floor(a.MaxHealth * 0.3)
				a.Move(CPos.New(4, a.Location.Y))
			end
		end
		local runner = xenos.GetActorsByType("runner")[1]
		runner.Health = math.floor(runner.MaxHealth * 0.3)
		runner.Move(CPos.New(28, runner.Location.Y))
		marines.GetActorsByType("cryo-pod")[1].CallDropPod(CPos.New(16, 15), "sentry-turret")
		marines.GetActorsByType("workshop")[1].ActivateCondorStrike(CPos.New(22, 4), "orbital")
	end)
	Trigger.AfterDelay(140, function()
		print("DBG cade lost " .. (100000 - cade.Health) .. ", turret lost " .. (100000 - turret.Health))
	end)
end
