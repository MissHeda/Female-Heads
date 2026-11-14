#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Runs for every person when it is created: from then on its hair follows its headgear.
 *
 * Arguments:
 * 0: Unit <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [_unit] call mhfh_hair_fnc_initUnit;
 *
 * Public: No
 */

params [["_unit", objNull, [objNull]]];

if (isNull _unit) exitWith {};

// Fires for every slot; the function only looks at what the unit wears now, so nothing is
// filtered here.
_unit addEventHandler ["SlotItemChanged", {
    [_this select 0] call FUNC(updateHair);
}];

// A unit that changes hands (a player taking over an AI, a headless client) is looked at by
// its new owner.
_unit addEventHandler ["Local", {
    params ["_unit", "_isLocal"];

    if (_isLocal) then {
        [_unit] call FUNC(updateHair);
    };
}];

// The face is given to a new unit after its init, and a mission may still dress it: look once
// now and once when that is over.
[_unit] call FUNC(updateHair);
[{_this call FUNC(updateHair)}, [_unit], 1] call CBA_fnc_waitAndExecute;
