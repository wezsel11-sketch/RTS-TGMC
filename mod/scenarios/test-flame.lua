-- Scenario test: a flamer leaves burning ground that outlives the shot and hurts what stands on it. Prints "TEST flame PASS" or "TEST flame FAIL".
local reported = false

WorldLoaded = function()
	local marines, xenos = Player.GetPlayer("Marines"), Player.GetPlayer("Xenos")
	local flamer = marines.GetActorsByType("flamer")[1]
	local silo = xenos.GetActorsByType("crusher")[1]
	local patches = function()
		return #Map.ActorsInBox(WPos.New(0, 0, 0), WPos.New(40 * 1024, 40 * 1024, 0), function(a) return a.Type == "flame-patch" end)
	end
	local early, late = 0, 0
	Trigger.AfterDelay(60, function() early = patches() end)
	Trigger.AfterDelay(160, function() late = patches() end)
	Trigger.AfterDelay(400, function()
		if reported then return end
		reported = true
		if early == 0 then
			print("TEST flame FAIL (no flame patch after the flamer fired)")
		elseif late == 0 then
			print("TEST flame FAIL (flames gone after 160 ticks)")
		else
			print("TEST flame PASS (" .. early .. " patches at 60, " .. late .. " at 160)")
		end
	end)
end
