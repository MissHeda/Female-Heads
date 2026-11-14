#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Turns the text of the two headgear settings into lists and forgets what was found out with
 * the old lists. An entry is a class name (classes inheriting from it count as well) or, with
 * * or ? in it, a pattern for the class name itself: * stands for any text, ? for one
 * character. Upper and lower case do not matter.
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

private _parse = {
    params ["_text"];

    private _classes = [];
    private _patterns = [];

    {
        if ("*" in _x || {"?" in _x}) then {
            // Class names only hold letters, digits and underscores, so nothing else in
            // them means anything to a regular expression.
            _patterns pushBack ((_x regexReplace ["\*", ".*"]) regexReplace ["\?", "."]);
        } else {
            _classes pushBack _x;
        };
    } forEach ((_text splitString _separators) select {_x isNotEqualTo ""});

    [_classes, _patterns]
};

([missionNamespace getVariable [QGVAR(braidHeadgear), ""]] call _parse) params ["_braidClasses", "_braidPatterns"];
([missionNamespace getVariable [QGVAR(bunHeadgear), ""]] call _parse) params ["_bunClasses", "_bunPatterns"];

GVAR(braidClasses) = _braidClasses;
GVAR(braidPatterns) = _braidPatterns;
GVAR(bunClasses) = _bunClasses;
GVAR(bunPatterns) = _bunPatterns;
GVAR(styleCache) = createHashMap;
