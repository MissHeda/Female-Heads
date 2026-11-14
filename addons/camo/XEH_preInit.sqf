#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

// Numbers
[
    QGVAR(duration),
    "SLIDER",
    [LLSTRING(SETTING_Duration), LLSTRING(SETTING_Duration_DESC)],
    [LELSTRING(hair,SETTING_Category), LLSTRING(SETTING_SubCategory)],
    [0, 30, 5, 0],
    1
] call CBA_fnc_addSetting;

// Switches
[
    QGVAR(enabled),
    "CHECKBOX",
    [LLSTRING(SETTING_Enabled), LLSTRING(SETTING_Enabled_DESC)],
    [LELSTRING(hair,SETTING_Category), LLSTRING(SETTING_SubCategory)],
    true,
    1
] call CBA_fnc_addSetting;

ADDON = true;
