-- Scenario test: ObjectiveBotModule (tgmc/code/Bots/). The marine bot has sixteen idle riflemen at its cryo pod, enough for the squad
-- manager to send squads at the xeno silo (60,4), away from the objective; the silo cannot fall, so a squad never comes back idle. Three disk terminals and the nuke stand on open ground and
-- no one is in the way (the xenos have no bot). The bot must decode the terminals and then arm the nuke: by tick 9000 the marines own
-- all three terminals and the nuke. Prints "TEST ai-distress PASS" or "TEST ai-distress FAIL".
local reported = false

WorldLoaded = function()
	local marines = Player.GetPlayer("Marines")

	local function report(ok, why)
		if not reported then
			reported = true
			print("TEST ai-distress " .. (ok and "PASS" or "FAIL") .. " (" .. why .. ")")
		end
	end

	local function check(tick)
		local disks = #marines.GetActorsByTypes({ "disk-terminal" })
		local nuke = #marines.GetActorsByTypes({ "nuke" })
		if disks >= 3 and nuke > 0 then
			report(true, "three disks and the nuke by tick " .. tick)
		elseif tick >= 9000 then
			report(false, "by tick 9000 the marines own " .. disks .. " disks and " .. nuke .. " nuke")
		else
			Trigger.AfterDelay(100, function() check(tick + 100) end)
		end
	end

	check(0)
end
