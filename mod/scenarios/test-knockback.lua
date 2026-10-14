-- Scenario test: a crusher's charge throws a marine several cells away. The marine holds fire and never walks, so any move is the throw.
-- Prints "TEST knockback PASS" or "TEST knockback FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	local marine = marines.GetActorsByType("rifleman")[1]
	local crusher = xenos.GetActorsByType("crusher")[1]
	marine.Stance = "HoldFire"
	local start = marine.Location.X
	Trigger.AfterDelay(15, function() crusher.Attack(marine, true, true) end)
	local function poll(ticks)
		if reported then
			return
		end
		local x = marine.IsDead and start or marine.Location.X
		if x >= start + 3 then
			reported = true
			print("TEST knockback PASS (marine from x " .. start .. " to " .. x .. " by tick " .. ticks .. ")")
		elseif ticks >= 800 then
			reported = true
			print("TEST knockback FAIL (marine at x " .. x .. ", hp " .. (marine.IsDead and 0 or marine.Health) .. ", crusher at " .. tostring(crusher.Location) .. ")")
		else
			Trigger.AfterDelay(5, function() poll(ticks + 5) end)
		end
	end
	Trigger.AfterDelay(5, function() poll(5) end)
end
