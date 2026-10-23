-- Not a test: a boiler bombards a squad and a bull charges it, for the xeno abilities screenshot (shot-xeno-kits map).
WorldLoaded = function()
	local xenos = Player.GetPlayer("Xenos")
	local target = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1]
	-- Something moves the camera back at the start: keep putting it on the action, as shot_map.py does.
	local at = target.CenterPosition + WVec.New(-4096, 0, 0)
	local function look()
		Camera.Position = at
		Trigger.AfterDelay(3, look)
	end
	look()
	Utils.Do(Player.GetPlayer("Marines").GetActorsByType("rifleman"), function(r) r.Stance = "HoldFire" end)
	Trigger.AfterDelay(40, function() xenos.GetActorsByType("boiler")[1].UseAbilityAt(1, target.Location) end)
	Trigger.AfterDelay(64, function() xenos.GetActorsByType("bull")[1].UseAbilityAt(1, target.Location + CVec.New(0, 2)) end)
end
