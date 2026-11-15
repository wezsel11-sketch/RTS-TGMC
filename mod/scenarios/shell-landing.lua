-- The menu's backdrop: the marines' Alamo lands at their base and the squad walks out (the landing intro), then the
-- two bots fight it out. The camera stays on the landing pad: the ship fills the middle of the screen, the base sits
-- just above the menu's row of cards.
WorldLoaded = function()
	Camera.Position = Map.CenterOfCell(CPos.New(28, 20))
end
