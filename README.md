# MH Female Heads

Female faces for Arma 3 on the head of
[Task Force Timberwolf Female Characters](https://steamcommunity.com/sharedfiles/filedetails/?id=2021778690) (Iceman).
Steam Workshop: [3840043520](https://steamcommunity.com/sharedfiles/filedetails/?id=3840043520)

![preview](docs/preview.jpg)

## Requirements

- Task Force Timberwolf Female Characters (`female3_ICEMAN`)
- CBA_A3
- ACE3 (optional): self interaction Equipment > Face

## Faces

`MHF_Female_<Name>_<Bun|Braid>[_Tactical]`, e.g. `MHF_Female_Kavanagh_Braid_Tactical`.

| Name | Hair | Skin | Eyes |
|---|---|---|---|
| Kovacs | black | pale | grey |
| Reyes | dark brown | tan | brown |
| Okoye | black | dark | dark |
| Kavanagh | auburn | fair, freckles | green |
| Lindqvist | platinum blonde | pale | blue |
| Fraser | ginger | fair, freckles | green |
| Novak | light brown | medium | hazel |
| Carter, Medrano | Timberwolf faces | | |

`B_female_bun_01`..`04` stay valid but are hidden from face lists (`disabled = 1`).

## Settings (CBA, "MH Female Heads")

| Setting | Default | Scope |
|---|---|---|
| Hair follows the headgear | on | client |
| Without headgear | as picked | client |
| All other headgear | bun | client |
| Headgear worn with the braid | `H_Cap_red, H_Cap_headphones` | client |
| Headgear worn with the bun | empty | client |
| Camo cream actions | on | server |
| Camo cream time | 5 s | server |

Headgear lists: class names (inheritance counts) or patterns with `*` and `?`. Client settings can be forced by
the server.

## Config for other mods

| Key | Class | Meaning |
|---|---|---|
| `mhfh_keepBraid = 1;` | CfgWeapons headgear | braid under this headgear |
| `mhfh_bunFace = "<face>";` | CfgFaces, braid face | its bun face |
| `mhfh_braidFace = "<face>";` | CfgFaces, bun face | its braid face |
| `mhfh_hairStyles[] = {"bun", "<face>", "braid", "<face>"};` | CfgFaces | styles for the ACE hair action |
| `mhfh_camoFace = "<face>";` | CfgFaces, plain face | its painted face |
| `mhfh_plainFace = "<face>";` | CfgFaces, painted face | its plain face |

## Build

- `hemtt build` / `hemtt release`
- `tools/characters.py` generates textures, models and config in `addons/heads` (needs the TFTW files in
  `tools/ref`, see `tools/ref_tftw.py`); `tools/characters.py originals` only Carter and Medrano.
- Offline checks: `tools/preview_data.py`, `tools/simulate.py`, `tools/blender/sheet.py`, `tools/preview_sheet.py`.

## Credits

- Head model, face textures and face paint: Task Force Timberwolf Female Characters by Iceman.
  This addon contains content derived from TFTW Female Characters. Credit for this content go to Iceman. See
  https://steamcommunity.com/sharedfiles/filedetails/?id=2021778690 for more details
- Skeleton in `model.cfg`: Arma 3 Samples, Bohemia Interactive.
