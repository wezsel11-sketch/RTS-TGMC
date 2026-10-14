-- Scenario test: a marine or xeno that attacks an enemy ends up facing it, whichever way the enemy is. Four marines each shoot a
-- hunter standing north, east, south and west of them, and four hunters each claw a marine in the same four places.
-- Prints "TEST facing PASS" or "TEST facing FAIL". Facing 0 is north, 256 west, 512 south and 768 east.
local expected = { N = 0, W = 256, S = 512, E = 768 }

local function off(a, b)
	local d = math.abs(a - b) % 1024
	return math.min(d, 1024 - d)
end

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local pairs_ = {}
	-- marine group at x=8..., xeno group at x=40...: [marine, target dir]
	for _, r in ipairs(marines.GetActorsByType("rifleman")) do
		table.insert(pairs_, r)
	end
	local victims = xenos.GetActorsByType("hunter")
	for _, v in ipairs(victims) do
		v.Stance = "HoldFire"
	end

	local function check()
		local bad, log = {}, {}
		for _, a in ipairs(pairs_) do
			if not a.IsDead then
			local name = a.Type .. "@" .. a.Location.X .. "," .. a.Location.Y
			local want = nil
			for _, v in ipairs(victims) do
				if not v.IsDead then
					local dx, dy = v.Location.X - a.Location.X, v.Location.Y - a.Location.Y
					if dx * dx + dy * dy <= 36 and (a.Owner ~= v.Owner) then
						if math.abs(dx) > math.abs(dy) then want = dx > 0 and "E" or "W" else want = dy > 0 and "S" or "N" end
					end
				end
			end
			if want ~= nil then
				local f = a.Facing.Angle
				table.insert(log, name .. " wants " .. want .. " has " .. f)
				if off(f, expected[want]) > 90 then
					table.insert(bad, name .. " faces " .. f .. ", wanted " .. want)
				end
			end
			end
		end
		return bad, log
	end

	Trigger.AfterDelay(90, function()
		local bad, log = check()
		print("STAT " .. table.concat(log, "; "))
		print("TEST facing " .. (#bad == 0 and "PASS" or "FAIL") .. " (" .. #log .. " attackers checked" .. (#bad > 0 and ": " .. table.concat(bad, "; ") or "") .. ")")
	end)
end
