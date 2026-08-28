from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent
src = root / "assets_source"
out = root / "assets"
out.mkdir(exist_ok=True)

# Use the actual binary LOGO and ICON assets supplied by the user. These source
# files are stored directly in the R8 branch to avoid corruption from text/base64
# transport. The originals remain preserved in the AUTOLEDGER project archive.
icon_source = src / "AUTOLEDGER_ICON.png"
logo_source = src / "AUTOLEDGER_LOGO_MODERN.png"

icon = Image.open(icon_source).convert("RGBA")
logo = Image.open(logo_source).convert("RGB")

# Runtime copies used by the application UI.
icon.save(out / "AUTOLEDGER_ICON.png", format="PNG", optimize=True)
logo.save(out / "AUTOLEDGER_LOGO_MODERN.png", format="PNG", optimize=True)

# Conventional multi-resolution Windows application/shortcut icon.
icon_256 = icon.resize((256, 256), Image.Resampling.LANCZOS)
icon_256.save(
    out / "AUTOLEDGER_ICON.ico",
    format="ICO",
    sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(96,96),(128,128),(256,256)],
)
print("Generated AUTOLEDGER supplied LOGO/ICON assets")
