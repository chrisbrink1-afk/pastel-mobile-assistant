from pathlib import Path
import base64
from PIL import Image

root = Path(__file__).resolve().parent
src = root / "assets_source"
out = root / "assets"
out.mkdir(exist_ok=True)

for name in ["AUTOLEDGER_ICON.png", "AUTOLEDGER_LOGO_MODERN.png"]:
    data = base64.b64decode((src / f"{name}.b64").read_text(encoding="ascii"))
    (out / name).write_bytes(data)

icon = Image.open(out / "AUTOLEDGER_ICON.png").convert("RGBA")
icon.save(
    out / "AUTOLEDGER_ICON.ico",
    format="ICO",
    sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(96,96),(128,128),(256,256)],
)
print("Generated AUTOLEDGER supplied LOGO/ICON assets")
