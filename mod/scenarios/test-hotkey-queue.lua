-- Scenario test (see mod/test_scenarios.sh): the production queue path refuses an item the player cannot build (no mech without a
-- workshop), and accepts an affordable-later item with no cash, which then waits for money. Prints "TEST hotkey-queue PASS" or FAIL.
local done = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")
	marines.Cash = 0
	Trigger.AfterDelay(10, function()
		local unbuildable = marines.QueueUnit("mech")
		local waiting = marines.QueueUnit("rifleman")
		if not done then
			done = true
			if not unbuildable and waiting then
				print("TEST hotkey-queue PASS (unbuildable refused, unaffordable queued and waits)")
			else
				print("TEST hotkey-queue FAIL (unbuildable=" .. tostring(unbuildable) .. ", waiting=" .. tostring(waiting) .. ")")
			end
		end
	end)
end
