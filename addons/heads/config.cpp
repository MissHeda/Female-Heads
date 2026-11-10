class CfgPatches {
    class mhfh_heads {
        name = "MH Female Heads - Heads";
        author = "Miss Heda";
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.18;
        requiredAddons[] = {"mhfh_main", "A3_Characters_F", "A3_Characters_F_Heads"};
    };
};

// The head model is skinned to the face bones of OFP2_ManSkeleton, so the vanilla
// face animations (talking, blinking, expressions) drive it like any vanilla head.
class CfgHeads {
    class Default_A3;
    class DefaultHead_A3: Default_A3 {};
    class mhfh_female_bun: DefaultHead_A3 {
        model = "\z\mhfh\addons\heads\models\fh_head_bun.p3d";
        selectionHeadWound = "injury_head";
        selectionPersonality = "personality";
    };
};

class CfgFaces {
    class Default;
    class Man_A3: Default {
        class Default;
        class mhfh_female_bun_light: Default {
            author = "Miss Heda";
            displayName = "Female, Bun (Light)";
            head = "mhfh_female_bun";
            identityTypes[] = {};
            texture = "\z\mhfh\addons\heads\data\fh_light_co.paa";
            material = "\z\mhfh\addons\heads\data\fh_light.rvmat";
            materialWounded1 = "\z\mhfh\addons\heads\data\fh_light_injury.rvmat";
            materialWounded2 = "\z\mhfh\addons\heads\data\fh_light_injury.rvmat";
            textureHL = "\A3\Characters_F\Heads\Data\hl_white_bald_co.paa";
            materialHL = "\A3\Characters_F\Heads\Data\hl_white_bald_muscular.rvmat";
            textureHL2 = "\A3\Characters_F\Heads\Data\hl_white_bald_co.paa";
            materialHL2 = "\A3\Characters_F\Heads\Data\hl_white_bald_muscular.rvmat";
            disabled = 0;
        };
        class mhfh_female_bun_dark: mhfh_female_bun_light {
            displayName = "Female, Bun (Dark)";
            texture = "\z\mhfh\addons\heads\data\fh_dark_co.paa";
            material = "\z\mhfh\addons\heads\data\fh_dark.rvmat";
            materialWounded1 = "\z\mhfh\addons\heads\data\fh_dark_injury.rvmat";
            materialWounded2 = "\z\mhfh\addons\heads\data\fh_dark_injury.rvmat";
            textureHL = "\A3\Characters_F\Heads\Data\hl_black_bald_co.paa";
            materialHL = "\A3\Characters_F\Heads\Data\hl_black_bald_muscular.rvmat";
            textureHL2 = "\A3\Characters_F\Heads\Data\hl_black_bald_co.paa";
            materialHL2 = "\A3\Characters_F\Heads\Data\hl_black_bald_muscular.rvmat";
        };
    };
};
