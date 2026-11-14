#define COMPONENT hair
#define COMPONENT_BEAUTIFIED Hair
#include "\z\mhfh\addons\main\script_mod.hpp"
#include "\z\mhfh\addons\main\script_macros.hpp"

// A face names the same character with the other hair: a braid face its bun face
// (mhfh_bunFace), a bun face its braid face (mhfh_braidFace).
#define CFG_FACE(name) (configFile >> "CfgFaces" >> "Man_A3" >> (name))
#define BUN_FACE(name) (getText (CFG_FACE(name) >> "mhfh_bunFace"))
#define BRAID_FACE(name) (getText (CFG_FACE(name) >> "mhfh_braidFace"))

// The face a unit had before its hair was changed for its headgear. Public, so the machine
// that owns the unit later knows what to give back.
#define OWN_VAR QGVAR(ownFace)

// What a piece of headgear (or none) asks for - the values of the list settings.
#define STYLE_KEEP 0
#define STYLE_BRAID 1
#define STYLE_BUN 2

// How often the player's own face is looked at. Headgear changes are caught by an event, this
// is only for a face picked in an arsenal or set by a script while headgear is on.
#define PLAYER_CHECK_INTERVAL 0.5
