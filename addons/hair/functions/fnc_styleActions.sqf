#include "..\script_component.hpp"
/*
 * Author: Miss Heda
 * The entries below "Hair" in the ACE self interaction menu: one for every other hair style
 * the unit's character comes with (its face lists them in mhfh_hairStyles[], as pairs of
 * style and face).
 *
 * Arguments:
 * 0: Unit <OBJECT>
 *
 * Return Value:
 * Actions in the format ACE expects from an insertChildren code <ARRAY>
 *
 * Example:
 * [player] call mhfh_hair_fnc_styleActions;
 *
 * Public: No
 */

params [["_unit", objNull, [objNull]]];

private _face = face _unit;
private _styles = getArray (CFG_FACE(_face) >> STYLES_KEY);
private _actions = [];

for "_i" from 0 to (count _styles - 2) step 2 do {
    private _style = _styles select _i;
    private _styleFace = _styles select (_i + 1);

    if (toLowerANSI _styleFace isNotEqualTo toLowerANSI _face) then {
        // Styles this addon knows have a translated name, others show as they are written.
        private _key = format ["STR_mhfh_hair_STYLE_%1", _style];
        private _title = [_style, localize _key] select (isLocalized _key);

        private _action = [
            format [QGVAR(style_%1), _style],
            _title,
            "",
            {
                params ["", "_player", "_styleFace"];
                [_player, _styleFace] call FUNC(restyle);
            },
            {true},
            {},
            _styleFace
        ] call ace_interact_menu_fnc_createAction;

        _actions pushBack [_action, [], _unit];
    };
};

_actions
