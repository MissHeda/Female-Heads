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
// Faces of another mod that come with a bun and with a braid take part when they name each
// other in their CfgFaces classes: the braid face with mhfh_bunFace = "<bun face>"; the bun
// face with mhfh_braidFace = "<braid face>";
