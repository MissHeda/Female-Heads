#define COMPONENT hair
#define COMPONENT_BEAUTIFIED Hair
#include "\z\mhfh\addons\main\script_mod.hpp"
#include "\z\mhfh\addons\main\script_macros.hpp"

// Where a face says which face to wear instead while the braid has no room.
#define CFG_FACE(name) (configFile >> "CfgFaces" >> "Man_A3" >> (name))
#define BUN_FACE(name) (getText (CFG_FACE(name) >> "mhfh_bunFace"))

// The braid face a unit had before it was given the bun. Public, so the machine that owns the
// unit later knows what to give back.
#define BRAID_VAR QGVAR(braidFace)

// How often the player's own face is looked at. Headgear changes are caught by an event, this
// is only for a face picked in an arsenal or set by a script while a helmet is on.
#define PLAYER_CHECK_INTERVAL 0.5
