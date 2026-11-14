#define COMPONENT camo
#define COMPONENT_BEAUTIFIED Camo Cream
#include "\z\mhfh\addons\main\script_mod.hpp"
#include "\z\mhfh\addons\main\script_macros.hpp"

// A face names the same face with face paint (mhfh_camoFace) or without it (mhfh_plainFace).
#define CFG_FACE(name) (configFile >> "CfgFaces" >> "Man_A3" >> (name))
#define CAMO_KEY "mhfh_camoFace"
#define PLAIN_KEY "mhfh_plainFace"

// The face the hair addon remembers for a unit whose hair it changed for the headgear.
#define HAIR_OWN_VAR "mhfh_hair_ownFace"
