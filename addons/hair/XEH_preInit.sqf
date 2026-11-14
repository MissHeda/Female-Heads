#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

// Headgear classes the braid fits under, as typed into the setting, and what was found out
// about every headgear class asked about so far.
GVAR(keepClasses) = [];
GVAR(keepCache) = createHashMap;

// The switch for the whole feature: no sub-category, so it sits above everything else.
[
    QGVAR(enabled),
    "CHECKBOX",
    [LLSTRING(SETTING_Enabled), LLSTRING(SETTING_Enabled_DESC)],
    LLSTRING(SETTING_Category),
    true,
    1,
    {call FUNC(updateAll)}
] call CBA_fnc_addSetting;

// Text boxes
[
    QGVAR(braidHeadgear),
    "EDITBOX",
    [LLSTRING(SETTING_BraidHeadgear), LLSTRING(SETTING_BraidHeadgear_DESC)],
    [LLSTRING(SETTING_Category), LLSTRING(SETTING_SubCategory_Braid)],
    "H_Cap_red, H_Cap_headphones",
    1,
    {
        call FUNC(parseHeadgear);
        call FUNC(updateAll);
    }
] call CBA_fnc_addSetting;

ADDON = true;
