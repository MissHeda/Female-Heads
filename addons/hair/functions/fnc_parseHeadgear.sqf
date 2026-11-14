#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Turns the text of the two headgear settings into lists of classes and forgets what was
 * found out with the old lists.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * call mhfh_hair_fnc_parseHeadgear;
 *
 * Public: No
 */

// Commas, semicolons, spaces and line breaks all separate; quotes around a name are dropped.
private _separators = ", ;""'" + toString [9, 10, 13];

GVAR(braidClasses) = ((missionNamespace getVariable [QGVAR(braidHeadgear), ""]) splitString _separators) select {_x isNotEqualTo ""};
GVAR(bunClasses) = ((missionNamespace getVariable [QGVAR(bunHeadgear), ""]) splitString _separators) select {_x isNotEqualTo ""};
GVAR(styleCache) = createHashMap;
