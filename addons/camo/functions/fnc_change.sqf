#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Has a unit put camo cream on or take it off: after the time from the settings (shown as
 * ACE's progress bar, which the player can cancel) its face changes.
 *
 * Arguments:
 * 0: Unit <OBJECT>
 * 1: true: put it on, false: take it off <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, true] call mhfh_camo_fnc_change;
 *
 * Public: Yes
 */

params [["_unit", objNull, [objNull]], ["_toCamo", true, [true]]];

if !([_unit, _toCamo] call FUNC(canChange)) exitWith {};

private _duration = missionNamespace getVariable [QGVAR(duration), 5];

// No waiting asked for, somebody else's unit, or no ACE to draw the bar: at once.
if (_duration <= 0 || {_unit isNotEqualTo (call CBA_fnc_currentUnit)} || {isNil "ace_common_fnc_progressBar"}) exitWith {
    [_unit, _toCamo] call FUNC(apply);
};

[
    _duration,
    [_unit, _toCamo],
    {(_this select 0) call FUNC(apply)},
    {},
    [LLSTRING(Removing), LLSTRING(Applying)] select _toCamo
] call ace_common_fnc_progressBar;
