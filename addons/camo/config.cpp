#include "script_component.hpp"

// ACE is not required: without ace_interact_menu the actions are simply not there.
class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "mhfh_main",
            "mhfh_heads",
            "mhfh_hair",
            "cba_main",
            "cba_settings",
            "cba_xeh"
        };
        author = "Miss Heda";
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"

// Faces of another mod take part when they name each other in their CfgFaces classes: the
// plain face with mhfh_camoFace = "<painted face>"; the painted face with
// mhfh_plainFace = "<plain face>";
