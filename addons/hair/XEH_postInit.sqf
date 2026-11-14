#include "script_component.hpp"

// Settings can finish loading either side of this file.
call FUNC(parseHeadgear);
["CBA_SettingsInitialized", {
    call FUNC(parseHeadgear);
    call FUNC(updateAll);
}] call CBA_fnc_addEventHandler;

if (!hasInterface) exitWith {};

// With ACE: "Hair" in the self interaction menu (Equipment), with one entry for every other
// hair style the character comes with.
if (isClass (configFile >> "CfgPatches" >> "ace_interact_menu")) then {
    private _hair = [
        QGVAR(hair),
        LLSTRING(Action_Hair),
        "",
        {},
        {
            params ["", "_player"];
            count getArray (CFG_FACE(face _player) >> STYLES_KEY) > 2
        },
        {
            params ["", "_player"];
            [_player] call FUNC(styleActions)
        }
    ] call ace_interact_menu_fnc_createAction;

    ["CAManBase", 1, ["ACE_SelfActions", "ACE_Equipment"], _hair, true] call ace_interact_menu_fnc_addActionToClass;
};

// Putting a helmet on or taking it off is caught by an event on the unit (fnc_initUnit). A
// face picked in an arsenal or set by a script while the helmet is on is not, so the unit the
// player is in (and the one an arsenal is showing) is looked at a few times a second.
[{
    [call CBA_fnc_currentUnit] call FUNC(updateHair);

    private _center = missionNamespace getVariable ["BIS_fnc_arsenal_center", objNull];
    if (!isNull _center) then {
        [_center] call FUNC(updateHair);
    };
}, PLAYER_CHECK_INTERVAL] call CBA_fnc_addPerFrameHandler;
