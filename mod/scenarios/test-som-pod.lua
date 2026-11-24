-- Scenario test: the human player is SOM. Its drop pod lands SOM troops and no marines.
-- Prints "TEST som-pod PASS" or "TEST som-pod FAIL".
WorldLoaded = function()
	local som = Player.GetPlayer("Marines")
	local pod = som.GetActorsByType("cryo-pod")[1]
	Trigger.AfterDelay(10, function() pod.CallDropPod(CPos.New(15, 11), "som_trooper") end)
	Trigger.AfterDelay(300, function()
		local troopers = #som.GetActorsByType("som_trooper")
		local riflemen = #som.GetActorsByType("rifleman")
		print("TEST som-pod " .. ((troopers >= 4 and riflemen == 0) and "PASS" or "FAIL") .. " (" .. troopers .. " troopers, " .. riflemen .. " riflemen)")
	end)
end
