#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Has a unit do its hair another way: after a few seconds (ACE's progress bar, which the
 * player can cancel) it has the given face. That face then counts as the one picked for the
 * unit, so the headgear rules go on from it: put up in a bun by hand, it stays a bun without
 * a helmet too.
 *
 * Arguments:
 * 0: Unit <OBJECT>
 * 1: Face with the wanted hair style <STRING>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, "MHFH_Fraser_Bun"] call mhfh_hair_fnc_restyle;
 *
 * Public: Yes
 */

params [["_unit", objNull, [objNull]], ["_styleFace", "", [""]]];

if (isNull _unit || {!alive _unit} || {!isClass CFG_FACE(_styleFace)}) exitWith {};

private _apply = {
    params ["_unit", "_styleFace"];

    if (!alive _unit) exitWith {};

    _unit setVariable [OWN_VAR, nil, true];

    // setFace only changes the face on the machine it runs on.
    _unit setFace _styleFace;
    [_unit, _styleFace] remoteExec ["setFace", 0, _unit];

    // What is on the head may ask for something else right away.
    [_unit] call FUNC(updateHair);
};

// Somebody else's unit, or no ACE to draw the bar: at once.
if (_unit isNotEqualTo (call CBA_fnc_currentUnit) || {isNil "ace_common_fnc_progressBar"}) exitWith {
    [_unit, _styleFace] call _apply;
};

[
    RESTYLE_TIME,
    [_unit, _styleFace, _apply],
    {
        (_this select 0) params ["_unit", "_styleFace", "_apply"];
        [_unit, _styleFace] call _apply;
    },
    {},
    LLSTRING(Restyling)
] call ace_common_fnc_progressBar;
