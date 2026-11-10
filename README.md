# MH Female Heads

More female characters for Arma 3, built on the female head of
[Task Force Timberwolf Female Characters](https://steamcommunity.com/sharedfiles/filedetails/?id=2021778690) by Iceman.
That mod has to be loaded: normal and ambient maps, the hand material and the base classes come from it.

![preview](docs/preview.jpg)

## Faces

Every character also has a "(Tactical)" variant with face paint.

| Class | Name | Look |
|---|---|---|
| `mhfh_kovacs` | Kovacs | black hair, pale skin, grey eyes |
| `mhfh_reyes` | Reyes | dark brown hair, tan skin, brown eyes |
| `mhfh_okoye` | Okoye | black hair, dark skin, dark eyes |
| `mhfh_walsh` | Walsh | auburn hair, fair skin, freckles, green eyes |
| `mhfh_lindqvist` | Lindqvist | platinum blonde, pale skin, blue eyes |
| `mhfh_fraser` | Fraser | ginger hair, fair skin, freckles, green eyes |
| `mhfh_novak` | Novak | light brown hair, hazel eyes |
| `mhfh_haddad` | Haddad | black hair, olive skin, brown eyes |

Pick them in the Arsenal (Face) or with `player setFace "mhfh_walsh"` / `"mhfh_walsh_tac"`.

## How they are made

`tools/ref_tftw.py` reads the Timberwolf files from the Steam Workshop folder into `tools/ref` (not in this
repository). `tools/characters.py` then writes everything in `addons/heads`:

- **Textures:** one of the two Timberwolf faces with a new skin tone, hair, brow and eye colour and optional
  freckles (`tools/tftw_masks.py` finds skin, hair, brows, lips and iris in their texture layout); their face paint
  is laid over it for the Tactical variant; the hand texture gets the same skin tone.
- **Models:** the Timberwolf head with a slightly different face shape per character (jaw, chin, nose, cheeks,
  lips, brow). Skull, ears, neck, eye region, UVs and bone weights stay as they are, so helmets, uniforms and the
  face animations behave exactly like on the original head.
- **Config:** `config.cpp` and the model classes in `model.cfg`.

Add a character by adding an entry to `CHARS` in `tools/characters.py` and running it.

## Checks without starting the game

- `tools/simulate.py` replays the vanilla face animations (binarized RTMs from `characters_f\heads\anim`, read by
  `tools/rtm.py`) on a binarized model taken from the built PBO (`tools/pbox.py`, `tools/odump.mjs`). The new heads
  move like the Timberwolf head (viseme A: 9.9 mm on both).
- `tools/blender/sheet.py` renders all characters in an open Blender.

## Credits

- Head model, face textures and face paint: Task Force Timberwolf Female Characters by Iceman.
- Skeleton in `model.cfg`: Arma 3 Samples, Bohemia Interactive.
