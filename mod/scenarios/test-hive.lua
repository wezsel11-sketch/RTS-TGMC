-- Scenario test: a Forward Hive spreads weeds of its own and trains xenos, and a resin trap stings a marine that comes close.
-- Prints "TEST hive PASS" or "TEST hive FAIL".
local reported = false

WorldLoaded = function()
	local xenos, marines = Player.GetPlayer("Xenos"), Player.GetPlayer("Marines")
	local marine = marines.GetActorsByType("rifleman")[1]
	local start = marine.Health
	marine.Stance = "HoldFire"
	local runners = #xenos.GetActorsByType("runner")

	Trigger.AfterDelay(5, function()
		xenos.QueueUnit("runner")
	end)

	Trigger.AfterDelay(1500, function()
		if reported then return end
		reported = true
		local weeds = #xenos.GetActorsByType("weeds")
		local trained = #xenos.GetActorsByType("runner") - runners
		local stung = marine.IsDead or marine.Health < start
		if weeds < 3 then
			print("TEST hive FAIL (only " .. weeds .. " weeds from the hive)")
		elseif trained < 1 then
			print("TEST hive FAIL (the hive trained no runner)")
		elseif not stung then
			print("TEST hive FAIL (the resin trap did not sting the marine)")
		else
			print("TEST hive PASS (" .. weeds .. " weeds, " .. trained .. " runner trained, marine " .. start .. " -> " .. (marine.IsDead and 0 or marine.Health) .. ")")
		end
	end)
end
