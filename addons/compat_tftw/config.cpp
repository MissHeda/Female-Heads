// Optional: only loaded when Task Force Timberwolf Female Characters (female3_ICEMAN) is loaded as well.
// MH Female Heads has Carter and Medrano itself (MHF_Female_Carter_* / MHF_Female_Medrano_*), so Timberwolf's own
// classes are taken out of the face lists and every face shows once. They stay usable for everything that names them.
class CfgPatches {
    class mhfh_compat_tftw {
        name = "MH Female Heads - Timberwolf compatibility";
        author = "Miss Heda";
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.18;
        requiredAddons[] = {"mhfh_heads", "female3_ICEMAN"};
        skipWhenMissingDependencies = 1;
    };
};

class CfgFaces {
    class Default;
    class Man_A3: Default {
        class Default;
        class B_female_bun_01: Default {
            disabled = 1;
        };
        class B_female_bun_02: Default {
            disabled = 1;
        };
        class B_female_bun_03: Default {
            disabled = 1;
        };
        class B_female_bun_04: Default {
            disabled = 1;
        };
    };
};
