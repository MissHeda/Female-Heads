#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Makes the hair of a unit fit what it wears on its head. Every character exists with a bun
 * and with a braid; which one a unit shows follows the settings: one answer for no headgear,
 * one list of headgear for the braid, one for the bun, one answer for everything else. An
 * answer can also be "leave it": then the unit has the face that was picked for it.
 *
 * A face says in its config which face is the same character with a bun (mhfh_bunFace) or
 * with a braid (mhfh_braidFace). A bun names its braid, hair that hangs names the bun: a
 * face that names no bun face is a bun itself and stays where a bun is asked for.
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

// Not one of the faces that come with more than one hair style.
if (_bunFace isEqualTo "" && {_braidFace isEqualTo ""}) exitWith {
    if (_ownFace isNotEqualTo "") then {
        _unit setVariable [OWN_VAR, nil, true];
    };
};

// All faces of one character list the same hair styles; without a list they share her bun.
private _character = {
    params ["_name"];

    private _styles = getArray (CFG_FACE(_name) >> STYLES_KEY);
    if (count _styles > 1) exitWith {toLowerANSI (_styles select 1)};

    private _bun = BUN_FACE(_name);
    toLowerANSI ([_bun, _name] select (_bun isEqualTo ""))
};

// Somebody gave the unit another character in the meantime: what was remembered is void.
if (_ownFace isNotEqualTo "" && {(_ownFace call _character) isNotEqualTo (_face call _character)}) then {
    _ownFace = "";
    _unit setVariable [OWN_VAR, nil, true];
};

private _style = if (missionNamespace getVariable [QGVAR(enabled), true]) then {
    [headgear _unit] call FUNC(headgearStyle)
} else {
    STYLE_KEEP
};

// A face that names no braid face is the braid itself, one that names no bun face a bun.
// Where a bun is asked for and the picked face is a bun of another kind, that one is worn.
private _wanted = switch (_style) do {
    case STYLE_BRAID: {[_braidFace, _face] select (_braidFace isEqualTo "")};
    case STYLE_BUN: {
        if (_bunFace isEqualTo "") exitWith {_face};
        [_bunFace, _ownFace] select (_ownFace isNotEqualTo "" && {BUN_FACE(_ownFace) isEqualTo ""})
    };
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
