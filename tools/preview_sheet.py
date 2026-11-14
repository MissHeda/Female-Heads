"""docs/preview.jpg from the rendered sheets (tools/blender/sheet.py, all four variants): one row per character
with her bun from the front and the side, her braid from behind and the Tactical variant.
usage (repo root): python -I tools/preview_sheet.py
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(HERE, "out")
IDS = ["kovacs", "reyes", "okoye", "walsh", "lindqvist", "fraser", "novak"]
TILES = (("", 0), ("", 1), ("", 2), ("_braid", 2), ("_braid", 3), ("_braid_tac", 1))    # (variant, view)
S = 512; T = 300

sheet = Image.new("RGB", (T * len(TILES), T * len(IDS)))
for r, cid in enumerate(IDS):
    for c, (suffix, view) in enumerate(TILES):
        im = Image.open(os.path.join(O, f"sheet_{cid}{suffix}.png")).convert("RGB")
        sheet.paste(im.crop((view * S, 0, (view + 1) * S, S)).resize((T, T), Image.LANCZOS), (c * T, r * T))
sheet.save(os.path.join(HERE, "..", "docs", "preview.jpg"), quality=88)
print("docs/preview.jpg", sheet.size)
