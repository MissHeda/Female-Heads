#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Looks at the hair of every unit this machine owns. Used when a setting changes.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * call mhfh_hair_fnc_updateAll;
 *
 * Public: No
 */

{
    [_x] call FUNC(updateHair);
} forEach (allUnits select {local _x});
