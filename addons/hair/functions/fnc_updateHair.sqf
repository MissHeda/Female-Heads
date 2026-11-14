#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Makes the hair of a unit fit what it wears on its head. A unit with a braid face is given
 * the bun version of that face while its headgear leaves no room for the braid, and gets its
 * braid back when the headgear comes off or is one the braid fits under.
 *
 * Only the machine that owns the unit acts; the face change is sent to everyone, late joiners
 * included.
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
private _braidFace = _unit getVariable [BRAID_VAR, ""];

private _setFace = {
    params ["_unit", "_newFace"];

    // setFace only changes the face on the machine it runs on.
    _unit setFace _newFace;
    [_unit, _newFace] remoteExec ["setFace", 0, _unit];
};

// Switched off: whoever was given a bun gets the braid back, nobody is touched after that.
if !(missionNamespace getVariable [QGVAR(enabled), true]) exitWith {
    if (_braidFace isNotEqualTo "") then {
        if (toLowerANSI _face isEqualTo toLowerANSI BUN_FACE(_braidFace)) then {
            [_unit, _braidFace] call _setFace;
        };
        _unit setVariable [BRAID_VAR, nil, true];
    };
};

private _keepsBraid = [headgear _unit] call FUNC(keepsBraid);

// Wearing a braid: fine unless the headgear is in the way.
if (_bunFace isNotEqualTo "") exitWith {
    if (_keepsBraid) then {
        if (_braidFace isNotEqualTo "") then {
            _unit setVariable [BRAID_VAR, nil, true];
        };
    } else {
        _unit setVariable [BRAID_VAR, _face, true];
        [_unit, _bunFace] call _setFace;
    };
};

// Not wearing a braid, and never had one taken away: nothing to do.
if (_braidFace isEqualTo "") exitWith {};

// Somebody gave the unit another face in the meantime: that one stays.
if (toLowerANSI _face isNotEqualTo toLowerANSI BUN_FACE(_braidFace)) exitWith {
    _unit setVariable [BRAID_VAR, nil, true];
};

if (_keepsBraid) then {
    _unit setVariable [BRAID_VAR, nil, true];
    [_unit, _braidFace] call _setFace;
};
