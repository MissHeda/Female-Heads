#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Turns the text of the headgear setting into the list of classes and forgets what was found
 * out with the old list.
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

private _text = missionNamespace getVariable [QGVAR(braidHeadgear), ""];

// Commas, semicolons, spaces and line breaks all separate; quotes around a name are dropped.
GVAR(keepClasses) = (_text splitString (", ;""'" + toString [9, 10, 13])) select {_x isNotEqualTo ""};
GVAR(keepCache) = createHashMap;
