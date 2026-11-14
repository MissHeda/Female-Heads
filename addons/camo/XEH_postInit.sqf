#include "script_component.hpp"

if (!hasInterface) exitWith {};

// The actions live in ACE's self-interaction menu, under Equipment.
if !(isClass (configFile >> "CfgPatches" >> "ace_interact_menu")) exitWith {};

private _apply = [
    QGVAR(apply),
    LLSTRING(Apply),
    "",
    {
        params ["", "_player"];
        [_player, true] call FUNC(change);
    },
    {
        params ["", "_player"];
        [_player, true] call FUNC(canChange)
    }
] call ace_interact_menu_fnc_createAction;

private _remove = [
    QGVAR(remove),
    LLSTRING(Remove),
    "",
    {
        params ["", "_player"];
        [_player, false] call FUNC(change);
    },
    {
        params ["", "_player"];
        [_player, false] call FUNC(canChange)
    }
] call ace_interact_menu_fnc_createAction;

["CAManBase", 1, ["ACE_SelfActions", "ACE_Equipment"], _apply, true] call ace_interact_menu_fnc_addActionToClass;
["CAManBase", 1, ["ACE_SelfActions", "ACE_Equipment"], _remove, true] call ace_interact_menu_fnc_addActionToClass;
