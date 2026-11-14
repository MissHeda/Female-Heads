#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Makes the hair of a unit fit what it wears on its head. Every character exists with a bun
 * and with a braid; which one a unit shows follows the settings: one answer for no headgear,
 * one list of headgear for the braid, one for the bun, one answer for everything else. An
 * answer can also be "leave it": then the unit has the face that was picked for it.
 *
 * Only the machine that owns the unit acts, by its own settings; the face change is sent to
 * everyone, late joiners included.
 *
 * Arguments:
 * 0: Unit <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player] call mhfh_hair_fnc_updateHair;
 *
 * Public: Yes
 */

params [["_unit", objNull, [objNull]]];

if (isNull _unit || {!local _unit} || {!alive _unit}) exitWith {};

private _face = face _unit;
private _bunFace = BUN_FACE(_face);
private _braidFace = BRAID_FACE(_face);
private _ownFace = _unit getVariable [OWN_VAR, ""];

// Not one of the faces that come in both versions.
if (_bunFace isEqualTo "" && {_braidFace isEqualTo ""}) exitWith {
    if (_ownFace isNotEqualTo "") then {
        _unit setVariable [OWN_VAR, nil, true];
    };
};

// A braid face names its bun face, a bun face its braid face.
private _hasBraid = _bunFace isNotEqualTo "";
private _otherFace = [_braidFace, _bunFace] select _hasBraid;

// Somebody gave the unit another character in the meantime: what was remembered is void.
if (_ownFace isNotEqualTo "" && {!(toLowerANSI _ownFace in [toLowerANSI _face, toLowerANSI _otherFace])}) then {
    _ownFace = "";
    _unit setVariable [OWN_VAR, nil, true];
};

private _style = if (missionNamespace getVariable [QGVAR(enabled), true]) then {
    [headgear _unit] call FUNC(headgearStyle)
} else {
    STYLE_KEEP
};

private _wanted = switch (_style) do {
    case STYLE_BRAID: {[_otherFace, _face] select _hasBraid};
    case STYLE_BUN: {[_face, _otherFace] select _hasBraid};
    default {[_ownFace, _face] select (_ownFace isEqualTo "")};
};

// Back at the face that was picked for the unit, or never away from it: nothing to remember.
if (_ownFace isNotEqualTo "" && {toLowerANSI _wanted isEqualTo toLowerANSI _ownFace}) then {
    _unit setVariable [OWN_VAR, nil, true];
};

if (toLowerANSI _wanted isEqualTo toLowerANSI _face) exitWith {};

// The first change away from the picked face: remember it.
if (_ownFace isEqualTo "") then {
    _unit setVariable [OWN_VAR, _face, true];
};

// setFace only changes the face on the machine it runs on.
_unit setFace _wanted;
[_unit, _wanted] remoteExec ["setFace", 0, _unit];
