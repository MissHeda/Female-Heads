# MH Female Heads

Female heads for Arma 3. Each head is skinned to the face bones of the vanilla
`OFP2_ManSkeleton`, so the vanilla face animations (talking, blinking, expressions)
drive it like any vanilla head. No scripts, no dependencies.

## Faces

| Class | Name |
|---|---|
| `mhfh_female_bun_light` | Female, Bun (Light) |
| `mhfh_female_bun_dark` | Female, Bun (Dark) |

Pick them in the Arsenal (Face) or with `player setFace "mhfh_female_bun_light"`.

## How the head is made

Everything is generated, nothing is hand-edited in Object Builder:

1. **Blender + MPFB** (CC0 MakeHuman assets): `tools/blender/01_human.py` creates the
   female base, `04_rig.py` adds the MakeHuman default rig (its face bones carry the
   weights), `05_parts.py` adds teeth and tongue, `06_build.py` cuts and decimates the head,
   `07_bun_uv.py` adds the bun and packs the texture atlas.
2. **Bakes:** `08_bake.py` bakes skin, brows, world position, normals and AO;
   `tools/compose_textures.py` paints hair and brows from the baked positions and writes
   `_co`, `_nohq` (DirectX green), `_smdi` and `_as`.
3. **Model:** `10_export.py` / `11_shadow.py` export the LODs, `tools/build_p3d.py` maps the
   MakeHuman face bones onto the Arma `Face_*` bones and writes the MLOD
   (LOD 1/2/4, closed shadow volume, memory points).
4. `tools/make_rvmats.py` writes the Skin-shader materials; PNGs go to PAA with ImageToPAA.

The Blender scripts run inside an open Blender via the local MCP bridge
(`node ~/.claude/blender-bridge/run.js <script>`).

## Credits

- Base mesh, skins and eyes: MakeHuman / MPFB system assets (CC0).
- Skeleton and `ArmaMan` model class: Arma 3 Samples, Bohemia Interactive.
- Inspired by the Task Force Timberwolf Female Characters by Iceman; no files of that mod are used.
