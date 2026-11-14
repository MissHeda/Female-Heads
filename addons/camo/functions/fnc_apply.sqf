#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Gives a unit its face with or without face paint, for everyone, late joiners included.
 *
 * Arguments:
 * 0: Unit <OBJECT>
 * 1: true: with face paint, false: without <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, true] call mhfh_camo_fnc_apply;
 *
 * Public: Yes
 */

params [["_unit", objNull, [objNull]], ["_toCamo", true, [true]]];

if (isNull _unit || {!alive _unit}) exitWith {};

private _key = [PLAIN_KEY, CAMO_KEY] select _toCamo;
private _face = getText (CFG_FACE(face _unit) >> _key);

if (_face isEqualTo "") exitWith {};

// The hair addon may have changed the hair for the headgear and remembers the face that was
// picked: that one gets the paint (or loses it) as well, or the paint would be gone again
// with the next helmet.
private _ownFace = _unit getVariable [HAIR_OWN_VAR, ""];

if (_ownFace isNotEqualTo "") then {
    private _ownChanged = getText (CFG_FACE(_ownFace) >> _key);

    if (_ownChanged isNotEqualTo "") then {
        _unit setVariable [HAIR_OWN_VAR, _ownChanged, true];
    };
};

// setFace only changes the face on the machine it runs on.
_unit setFace _face;
[_unit, _face] remoteExec ["setFace", 0, _unit];
