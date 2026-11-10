#include "script_version.hpp"
#define QUOTE(x) #x

class CfgPatches {
    class mhfh_main {
        name = "MH Female Heads";
        author = "Miss Heda";
        url = "https://github.com/MissHeda";
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.18;
        requiredAddons[] = {"A3_Characters_F"};
        versionStr = QUOTE(MAJOR.MINOR.PATCHLVL);
        versionAr[] = {MAJOR, MINOR, PATCHLVL};
    };
};
