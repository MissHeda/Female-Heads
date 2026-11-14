# MH Female Heads

More female characters for Arma 3, built on the female head of
[Task Force Timberwolf Female Characters](https://steamcommunity.com/sharedfiles/filedetails/?id=2021778690) by Iceman.
That mod has to be loaded: normal and ambient maps and the base classes come from it. CBA_A3 is needed as well.

![preview](docs/preview.jpg)

## Faces

Every character comes with a bun or a braid, each also as a Tactical version with face paint. The classes are
named `MHF_Female_<Name>_<Style>` and `MHF_Female_<Name>_<Style>_Tactical`, for example `MHF_Female_Walsh_Bun`,
`MHF_Female_Walsh_Braid_Tactical`. In the arsenal every style is followed by its Tactical version.

| Name | Look |
|---|---|
| Kovacs | black hair, pale skin, grey eyes |
| Reyes | dark brown hair, tan skin, brown eyes |
| Okoye | black hair, dark skin, dark eyes |
| Walsh | auburn hair, fair skin, freckles, green eyes |
| Lindqvist | platinum blonde, pale skin, blue eyes |
| Fraser | ginger hair, fair skin, freckles, green eyes |
| Novak | light brown hair, hazel eyes |

Pick them in the Arsenal (Face) or with `player setFace "MHF_Female_Walsh_Bun"`.

One more hair style is being tried out on Fraser only, with its Tactical version: a bun wound from a twisted
rope of hair (`MHF_Female_Fraser_BraidedBun`).

The four Timberwolf faces are listed under names of the same kind (`MHF_Female_Carter_Bun`,
`MHF_Female_Carter_Bun_Tactical`, `MHF_Female_Medrano_Bun`, `MHF_Female_Medrano_Bun_Tactical`). Their own classes
`B_female_bun_01` to `04` still work for everything that uses them, but are hidden from the face lists so every
face shows once.

## Braid and headgear

The braid starts high on the back of the head and comes out through the opening of a baseball cap. Under a
helmet there is no room for it. So the hair follows the headgear (`addons/hair`): every character exists with a
bun and with a braid, and which one she shows is decided by settings.

**Settings** (CBA, "MH Female Heads"). They are the player's own settings; a server or mission can force them
like any CBA setting.

| Setting | Default | |
|---|---|---|
| Hair follows the headgear | on | Off: always the hair of the face that was picked |
| Without headgear | As picked | As picked / Braid / Bun |
| All other headgear | Bun | For headgear that is in neither list |
| Headgear worn with the braid | `H_Cap_red, H_Cap_headphones` | Class names; classes inheriting from them count too. Covers all caps |
| Headgear worn with the bun | empty | Class names; goes before the braid list |

An entry with `*` or `?` in it is a pattern for the class name itself (`*` any text, `?` one character, case
does not matter): `H_Cap_*`, `*Beret*`, `H_Helmet?_*`.

**By hand:** with ACE3 loaded the self interaction menu has "Hair" under Equipment, with every other hair
style the character comes with. What is picked there counts as her own hair from then on: put up in a bun by
hand, it stays a bun without a helmet too.

**Other mods:** headgear can ask for the braid itself with `mhfh_keepBraid = 1;` in its `CfgWeapons` class.
Faces that come with a bun and with a braid take part when they name each other in `CfgFaces`:
`mhfh_bunFace = "<bun face>";` in a face with hanging hair, `mhfh_braidFace = "<braid face>";` in a bun face.
For the hair action a face lists all styles of its character as pairs of style and face:
`mhfh_hairStyles[] = {"bun", "<face>", "braid", "<face>"};`

## Camo cream

With ACE3 loaded the self interaction menu has "Apply camo cream" and "Remove camo cream" under Equipment
(`addons/camo`): they switch a character between her face and its Tactical version, after a few seconds shown
as a progress bar. Settings (server): the time it takes and a switch for the actions. Without ACE3 the faces are
simply picked as usual.

Faces of other mods take part with `mhfh_camoFace = "<painted face>";` in the plain face and
`mhfh_plainFace = "<plain face>";` in the painted one.

## How they are made

`tools/ref_tftw.py` reads the Timberwolf files from the Steam Workshop folder into `tools/ref` (not in this
repository). `tools/characters.py` then writes everything in `addons/heads`:

- **Textures:** one of the two Timberwolf faces with a new skin tone, brow and eye colour and optional freckles
  (`tools/tftw_masks.py` finds skin, hair, brows, lips and iris in their texture layout). The hair of every
  character is the photographed hair of the dark-haired Timberwolf face with its soft hairline, recoloured;
  on the other face the own blonde hair is replaced by skin first. On the braid variant the hair runs to the
  start of the braid instead of to the bun (`hair_to_braid`: the photo hair is moved up, with some fine drawn strands
  right around the start of the braid). The Tactical variant is the Timberwolf face paint laid over the new
  skin (`paint_layer` solves for the paint and how thick it lies, so it sits on any skin tone as on theirs). The iris keeps the light and dark of the photographed one and only changes its tint.
  The texture for arms and legs gets the tone of the neck and uses the same shader as the face
  (`mhfh_hl.rvmat`), so both have the same colour where they meet.
- **Models:** the Timberwolf head with a slightly different face shape per character (jaw, chin, nose, cheeks,
  lips, brow). Skull, ears, neck, eye region, UVs and bone weights stay as they are, so helmets, uniforms and the
  face animations behave exactly like on the original head. For the braid variant the bun is taken off and a
  braid is added (`tools/braid.py`): gathered hair, a hair tie, three strands plaited around each other, a second
  tie and the loose end. Hair cannot move by itself in the game, so it is shaped the way it would hang on
  someone standing upright, and only its first centimetres follow the head: the rest follows neck and upper
  spine and stays on the back when the head turns. The same file builds the braided bun.
- **Shadow:** `tools/shadow.py` repairs the shadow volume of the Timberwolf head, which throws dark streaks on
  the neck: three triangles that exist twice are removed, the points below the jaw get the bone weights of the
  visible surface next to them, and points outside the visible surface are moved inside.
- **Config:** `config.cpp` and the model classes in `model.cfg`.

Add a character by adding an entry to `CHARS` in `tools/characters.py` and running it.

## Checks without starting the game

- `tools/simulate.py` replays the vanilla face animations (binarized RTMs from `characters_f\heads\anim`, read by
  `tools/rtm.py`) on a binarized model taken from the built PBO (`tools/pbox.py`, `tools/odump.mjs`). The new heads
  move like the Timberwolf head (viseme A: 9.9 mm on both).
- `tools/preview_data.py` takes the binarized models out of the built PBO (and prints their skeleton);
  `blender -b --python tools/blender/sheet.py -- "" _braid _tac _braid_tac` renders all characters from them
  without opening Blender, `tools/preview_sheet.py` puts the picture above together.

## Credits

- Head model, face textures and face paint: Task Force Timberwolf Female Characters by Iceman.
- Skeleton in `model.cfg`: Arma 3 Samples, Bohemia Interactive.
