-- Scenario test: unit control, by the order a mouse click gives (ClickOrder, the test aid in tgmc/code/MinerField.cs).
--   right-click an enemy: attack.  right-click open ground: move.
--   Ctrl-click a fence (a neutral map object): forced attack, for a rifleman too.
--   Ctrl-click a wall cell: forced attack for a grenadier (grenades chip walls); nothing for a rifleman (bullets do not).
-- Then the grenadier is given that forced attack and the wall cell must fall. Prints "TEST click-force PASS" or FAIL.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local rifleman = marines.GetActorsByType("rifleman")[1]
	local grenadier = marines.GetActorsByType("grenadier")[1]
	local hunter = Player.GetPlayer("Xenos").GetActorsByType("hunter")[1]
	local fence = Player.GetPlayer("Neutral").GetActors()[1]
	for _, a in ipairs(Player.GetPlayer("Neutral").GetActors()) do
		if a.Type:find("^mapobj") then fence = a end
	end
	local wall, ground = CPos.New(14, 11), CPos.New(6, 6)
	rifleman.Stance = "HoldFire"
	grenadier.Stance = "HoldFire"
	hunter.Stance = "HoldFire"
	Trigger.AfterDelay(10, function()
		local r = {
			enemy = rifleman.ClickOrder(hunter),
			ground = rifleman.ClickOrderAt(ground),
			fence = rifleman.ClickOrder(fence, true),
			rifleWall = rifleman.ClickOrderAt(wall, true),
			grenadeWall = grenadier.ClickOrderAt(wall, true),
		}
		local ok = r.enemy:find("^Attack") and r.ground:find("^Move") and r.fence:find("^ForceAttack") and
			not r.rifleWall:find("Attack") and r.grenadeWall:find("^ForceAttack")
		local text = "enemy " .. r.enemy .. ", ground " .. r.ground .. ", fence " .. r.fence .. ", rifle on wall " .. r.rifleWall ..
			", grenade on wall " .. r.grenadeWall
		if not ok then
			print("TEST click-force FAIL (" .. text .. ")")
			return
		end
		grenadier.ForceAttackCell(wall)
		Trigger.AfterDelay(1500, function()
			local after = Map.TerrainType(wall)
			print("TEST click-force " .. (after ~= "Wall" and "PASS" or "FAIL") .. " (" .. text .. "; wall cell is " .. tostring(after) .. ")")
		end)
	end)
end
