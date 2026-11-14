#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

// Headgear classes as typed into the two text settings, and what was found out about every
// headgear class asked about so far.
GVAR(braidClasses) = [];
GVAR(bunClasses) = [];
GVAR(styleCache) = createHashMap;

// All of these are the player's own settings (a server or mission can still force them, as
// with every CBA setting): each machine decides for the units it owns.

// The switch for the whole feature: no sub-category, so it sits above everything else.
[
    QGVAR(enabled),
    "CHECKBOX",
    [LLSTRING(SETTING_Enabled), LLSTRING(SETTING_Enabled_DESC)],
    LLSTRING(SETTING_Category),
    true,
    0,
    {call FUNC(updateAll)}
] call CBA_fnc_addSetting;

// Lists
[
    QGVAR(noHeadgear),
    "LIST",
    [LLSTRING(SETTING_NoHeadgear), LLSTRING(SETTING_NoHeadgear_DESC)],
    [LLSTRING(SETTING_Category), LLSTRING(SETTING_SubCategory_Headgear)],
    [[STYLE_KEEP, STYLE_BRAID, STYLE_BUN], [LLSTRING(STYLE_Keep), LLSTRING(STYLE_Braid), LLSTRING(STYLE_Bun)], 0],
    0,
    {
        call FUNC(parseHeadgear);
        call FUNC(updateAll);
    }
] call CBA_fnc_addSetting;

[
    QGVAR(otherHeadgear),
    "LIST",
    [LLSTRING(SETTING_OtherHeadgear), LLSTRING(SETTING_OtherHeadgear_DESC)],
    [LLSTRING(SETTING_Category), LLSTRING(SETTING_SubCategory_Headgear)],
    [[STYLE_KEEP, STYLE_BRAID, STYLE_BUN], [LLSTRING(STYLE_Keep), LLSTRING(STYLE_Braid), LLSTRING(STYLE_Bun)], 2],
    0,
    {
        call FUNC(parseHeadgear);
        call FUNC(updateAll);
    }
] call CBA_fnc_addSetting;

// Text boxes
[
    QGVAR(braidHeadgear),
    "EDITBOX",
    [LLSTRING(SETTING_BraidHeadgear), LLSTRING(SETTING_BraidHeadgear_DESC)],
    [LLSTRING(SETTING_Category), LLSTRING(SETTING_SubCategory_Headgear)],
    "H_Cap_red, H_Cap_headphones",
    0,
    {
        call FUNC(parseHeadgear);
        call FUNC(updateAll);
    }
] call CBA_fnc_addSetting;

[
    QGVAR(bunHeadgear),
    "EDITBOX",
    [LLSTRING(SETTING_BunHeadgear), LLSTRING(SETTING_BunHeadgear_DESC)],
    [LLSTRING(SETTING_Category), LLSTRING(SETTING_SubCategory_Headgear)],
    "",
    0,
    {
        call FUNC(parseHeadgear);
        call FUNC(updateAll);
    }
] call CBA_fnc_addSetting;

ADDON = true;
