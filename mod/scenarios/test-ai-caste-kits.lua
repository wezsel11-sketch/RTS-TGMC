-- Scenario test: the xeno bot uses the abilities the castes' kits gained from TGMC on its own (AbilityBotModule in Bots.cs, each
-- ability's AiRange and AiMinTargets in units.yaml). Each caste stands beside two riflemen that hold fire; only the bot's ability module
-- is at work. Within 600 ticks each listed slot must have been used (it is seen not ready). Prints "TEST ai-caste-kits PASS" or
-- "TEST ai-caste-kits FAIL" with the slots never used.
local kits = {
	crusher = { 2 }, ravager = { 3, 4 }, defender = { 3 }, warlock = { 2, 3 }, pyrogen = { 2, 3, 4 },
	widow = { 2 }, carrier = { 3 }, puppeteer = { 2, 3 },
}
local order = { "crusher", "ravager", "defender", "warlock", "pyrogen", "widow", "carrier", "puppeteer" }

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	local xenos = Player.GetPlayer("Xenos")
	for _, m in ipairs(marines.GetActorsByType("rifleman")) do m.Stance = "HoldFire" end
	local used, actors = {}, {}
	for _, t in ipairs(order) do actors[t] = xenos.GetActorsByType(t)[1] end

	local done = false
	local function poll(ticks)
		if done then return end
		for t, slots in pairs(kits) do
			local x = actors[t]
			for _, s in ipairs(slots) do
				if not x.IsDead and not x.AbilityReady(s) then used[t .. ":" .. s] = true end
			end
		end
		local missing = {}
		for _, t in ipairs(order) do
			for _, s in ipairs(kits[t]) do
				if not used[t .. ":" .. s] then table.insert(missing, t .. ":" .. s) end
			end
		end
		if #missing == 0 then
			done = true
			print("TEST ai-caste-kits PASS (every ability used by tick " .. ticks .. ")")
		elseif ticks >= 600 then
			done = true
			print("TEST ai-caste-kits FAIL (never used: " .. table.concat(missing, ", ") .. ")")
		else
			Trigger.AfterDelay(1, function() poll(ticks + 1) end)
		end
	end
	poll(0)
end
