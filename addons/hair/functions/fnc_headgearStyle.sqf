#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * Says which hair a piece of headgear asks for. In this order:
 *   - no headgear: the "Without headgear" setting
 *   - in "Headgear worn with the bun": bun
 *   - in "Headgear worn with the braid": braid
 *   - a class that says so in its config (mhfh_keepBraid = 1): braid
 *   - anything else: the "All other headgear" setting
 * An entry of a list is a class (classes inheriting from it count as well) or a pattern with
 * * and ? for the class name itself.
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

    private _listed = {
        params ["_classes", "_patterns"];

        _classes findIf {_headgear isKindOf [_x, _cfgWeapons]} != -1
        || {_patterns findIf {_headgear regexMatch _x} != -1}
    };

    _style = call {
        if ([GVAR(bunClasses), GVAR(bunPatterns)] call _listed) exitWith {STYLE_BUN};
        if ([GVAR(braidClasses), GVAR(braidPatterns)] call _listed) exitWith {STYLE_BRAID};
        if (getNumber (_cfgWeapons >> _headgear >> "mhfh_keepBraid") == 1) exitWith {STYLE_BRAID};

        missionNamespace getVariable [QGVAR(otherHeadgear), STYLE_BUN]
    };

    GVAR(styleCache) set [_key, _style];
};

_style
