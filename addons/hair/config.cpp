#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "mhfh_main",
            "mhfh_heads",
            "cba_main",
            "cba_settings",
            "cba_xeh"
        };
        author = "Miss Heda";
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"

// Headgear of other mods can say by itself that a braid fits under it:
//
//   class CfgWeapons {
//       class My_Cap: ... {
//           mhfh_keepBraid = 1;
//       };
//   };
//
// The same works for a face of another mod that has a version without the braid:
// mhfh_bunFace = "<class of that face>"; in its CfgFaces class.
