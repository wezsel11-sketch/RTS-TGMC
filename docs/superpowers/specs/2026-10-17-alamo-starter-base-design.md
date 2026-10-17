# Alamo starter base: design

## Intent

Marines start on the map inside a landed dropship, the Alamo. It is their first base: their spawn point and the area they
can build in. Units come out of its hatch. Structures can be built in and around it. Nothing else changes for the marines' starting
economy or units.

Success: a marine player starts with the Alamo on the landing zone, can build around it, spawns every new unit at its hatch, and
loses spawn and build area only when the Alamo is destroyed.

## Design

- **Actor:** one building actor for the whole Alamo. Its footprint is the dropship layout from `_maps/shuttles/alamo.dmm`
  (11 cells wide). The dmm's pieces (`dropship_piece` front, left, right; hatch; shutters; floor) are drawn as the
  actor's sprite, not as separate actors.
- **Spawn:** the hatch cell is the exit point (`Exit` trait). The starting squad and every trained unit leave the hatch.
- **Build area:** the Alamo gives a marine build area around its footprint, the same mechanism the cryo pod uses for
  marines (`GivesBuildableArea`). Players and the marine bot can build in and around it.
- **Start:** the Alamo replaces the cryo pod in the landing-zone start for the marines. Xenos are unchanged.
- **Loss:** when the Alamo dies, its spawn and build area go with it. Structures the marines already built stay. The
  marines' spawn then falls back to the other marine buildings, if any.

## Out of scope

- Production at the Alamo (option 2 in brainstorming: rejected).
- Transport or moving the Alamo (option 3: rejected).
- Alamo as a reinforcement drop.

## Open items for the plan

- Exact footprint and hatch cell from the dmm (read once, then fixed in the rules).
- Sprite: the Alamo's pieces are drawn together into one sprite sheet, in the way other large structures are built.
- How the bot treats the Alamo: as a construction yard (like the cryo pod) so it builds around it.

## Testing

- Scenario: a marine starts on the Alamo; a new unit appears at the hatch cell.
- Scenario: a structure can be placed in the Alamo's build area and not outside it.
- Scenario: destroying the Alamo removes the build area and spawn.
- Balance: the marine AI still builds and spawns after the change (`scenario-ai`).
