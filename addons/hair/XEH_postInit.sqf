#include "script_component.hpp"

// Settings can finish loading either side of this file.
call FUNC(parseHeadgear);
["CBA_SettingsInitialized", {
    call FUNC(parseHeadgear);
    call FUNC(updateAll);
}] call CBA_fnc_addEventHandler;

if (!hasInterface) exitWith {};

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
