-- Scenario test: an idle engineer standing beside a broken ore field, with no order given. It must leave the field alone:
-- "TEST engineer-autorepair PASS" when the field is untouched after 600 ticks, "FAIL" when it was repaired or claimed by itself.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local neutral = Player.GetPlayer("Neutral")
	local field = neutral.GetActorsByType("miner-field")[1]
	local hp0 = field.Health
	Trigger.AfterDelay(600, function()
		if field.IsDead or not field.IsInWorld then
			print("TEST engineer-autorepair FAIL (field claimed without an order, marine miners " .. #marines.GetActorsByType("miner") .. ")")
		else
			local hp1 = field.Health
			print("TEST engineer-autorepair " .. (hp1 == hp0 and "PASS" or "FAIL") .. " (field health " .. hp0 .. " -> " .. hp1 .. ")")
		end
	end)
end
