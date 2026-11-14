#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Says which hair a piece of headgear asks for. In this order:
 *   - no headgear: the "Without headgear" setting
 *   - a class from "Headgear worn with the bun" (or one that inherits from it): bun
 *   - a class from "Headgear worn with the braid" (or one that inherits from it): braid
 *   - a class that says so in its config (mhfh_keepBraid = 1): braid
 *   - anything else: the "All other headgear" setting
 *
 * Arguments:
 * 0: Headgear class, "" for none <STRING>
 *
 * Return Value:
 * 0: leave the face as chosen, 1: braid, 2: bun <NUMBER>
 *
 * Example:
 * ["H_Cap_blk"] call mhfh_hair_fnc_headgearStyle;
 *
 * Public: Yes
 */

params [["_headgear", "", [""]]];

if (_headgear isEqualTo "") exitWith {
    missionNamespace getVariable [QGVAR(noHeadgear), STYLE_KEEP]
};

private _key = toLowerANSI _headgear;
private _style = GVAR(styleCache) get _key;

if (isNil "_style") then {
    private _cfgWeapons = configFile >> "CfgWeapons";

    _style = call {
        if (GVAR(bunClasses) findIf {_headgear isKindOf [_x, _cfgWeapons]} != -1) exitWith {STYLE_BUN};
        if (GVAR(braidClasses) findIf {_headgear isKindOf [_x, _cfgWeapons]} != -1) exitWith {STYLE_BRAID};
        if (getNumber (_cfgWeapons >> _headgear >> "mhfh_keepBraid") == 1) exitWith {STYLE_BRAID};

        missionNamespace getVariable [QGVAR(otherHeadgear), STYLE_BUN]
    };

    GVAR(styleCache) set [_key, _style];
};

_style
