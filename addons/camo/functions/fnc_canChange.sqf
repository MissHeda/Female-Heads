#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Says whether a unit can put camo cream on (its face exists with face paint) or take it off
 * (its face exists without).
 *
 * Arguments:
 * 0: Unit <OBJECT>
 * 1: true: put it on, false: take it off <BOOL>
 *
 * Return Value:
 * Possible <BOOL>
 *
 * Example:
 * [player, true] call mhfh_camo_fnc_canChange;
 *
 * Public: Yes
 */

params [["_unit", objNull, [objNull]], ["_toCamo", true, [true]]];

missionNamespace getVariable [QGVAR(enabled), true]
&& {alive _unit}
&& {getText (CFG_FACE(face _unit) >> ([PLAIN_KEY, CAMO_KEY] select _toCamo)) isNotEqualTo ""}
