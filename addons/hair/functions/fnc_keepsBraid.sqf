#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Says whether a braid fits under a piece of headgear: no headgear at all, a class from the
 * setting (or one that inherits from it), or a class that says so in its config
 * (mhfh_keepBraid = 1).
 *
 * Arguments:
 * 0: Headgear class, "" for none <STRING>
 *
 * Return Value:
 * The braid can stay <BOOL>
 *
 * Example:
 * ["H_Cap_blk"] call mhfh_hair_fnc_keepsBraid;
 *
 * Public: Yes
 */

params [["_headgear", "", [""]]];

if (_headgear isEqualTo "") exitWith {true};

private _key = toLowerANSI _headgear;
private _keeps = GVAR(keepCache) get _key;

if (isNil "_keeps") then {
    private _cfgWeapons = configFile >> "CfgWeapons";

    _keeps = getNumber (_cfgWeapons >> _headgear >> "mhfh_keepBraid") == 1
        || {GVAR(keepClasses) findIf {_headgear isKindOf [_x, _cfgWeapons]} != -1};

    GVAR(keepCache) set [_key, _keeps];
};

_keeps
