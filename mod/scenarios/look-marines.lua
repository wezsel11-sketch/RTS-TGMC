-- Not a test: a map to look at (mod/smoke.sh look-marines). Top row: marines at 100%, 80%, 55%, 30% and 10% health, so the
-- health bars, blood and limp show. Second row: a plain, a first, second and third rank rifleman, and one dying
-- (a corpse is left behind). It prints no TEST line, so mod/test_scenarios.sh ignores it.
WorldLoaded = function()
	local marines = Player.GetPlayer("Marines").GetActorsByType("rifleman")
	local fractions = { 100, 80, 55, 30, 10 }
	for i = 1, 5 do
		marines[i].Health = math.floor(marines[i].MaxHealth * fractions[i] / 100)
	end
	for i = 6, 8 do
		marines[i].GiveLevels(i - 5, true)
	end
	Trigger.AfterDelay(5, function() marines[9].Kill() end)
	Camera.Position = Map.CenterOfCell(CPos.New(10, 12))
end
