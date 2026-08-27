from pathlib import Path
import base64
from PIL import Image

root = Path(__file__).resolve().parent
src = root / "assets_source"
out = root / "assets"
out.mkdir(exist_ok=True)

# Recreate build assets from compact, source-controlled copies derived from the
# exact LOGO and ICON supplied by the user. The original uploads are preserved
# separately in the AUTOLEDGER project archive.
icon_bytes = base64.b64decode((src / "AUTOLEDGER_ICON_128.png.b64").read_text(encoding="ascii"))
icon_source = out / "AUTOLEDGER_ICON.png"
icon_source.write_bytes(icon_bytes)

logo_jpg = out / "AUTOLEDGER_LOGO_MODERN_SOURCE.jpg"
logo_jpg.write_bytes(base64.b64decode((src / "AUTOLEDGER_LOGO_MODERN.jpg.b64").read_text(encoding="ascii")))
logo = Image.open(logo_jpg).convert("RGB")
logo.save(out / "AUTOLEDGER_LOGO_MODERN.png", format="PNG", optimize=True)

# Produce a conventional multi-resolution Windows ICO. The compact source is
# 128px; Pillow creates the smaller entries and a 256px high-resolution entry.
icon = Image.open(icon_source).convert("RGBA")
icon_256 = icon.resize((256, 256), Image.Resampling.LANCZOS)
icon_256.save(
    out / "AUTOLEDGER_ICON.ico",
    format="ICO",
    sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(96,96),(128,128),(256,256)],
)
print("Generated AUTOLEDGER supplied LOGO/ICON assets")
