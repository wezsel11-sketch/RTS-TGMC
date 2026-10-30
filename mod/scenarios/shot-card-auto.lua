-- Not a test: keeps the camera on the rifleman for the autocast and range preview screenshot (shot-card-auto map).
WorldLoaded = function()
	local at = Player.GetPlayer("Marines").GetActorsByType("rifleman")[1].CenterPosition
	-- Something moves the camera back at the start: keep putting it on the rifleman, as shot-yell does.
	local function look()
		Camera.Position = at
		Trigger.AfterDelay(3, look)
	end
	look()
end
