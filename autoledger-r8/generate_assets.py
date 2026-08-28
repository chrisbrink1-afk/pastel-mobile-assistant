from pathlib import Path
import base64
from PIL import Image

root = Path(__file__).resolve().parent
src = root / "assets_source"
out = root / "assets"
out.mkdir(exist_ok=True)

# The first R8 CI run proved this source-controlled icon payload is valid.
# Keep using it and avoid the later direct-binary copy that was corrupted in transport.
icon_bytes = base64.b64decode((src / "AUTOLEDGER_ICON_128.png.b64").read_text(encoding="ascii"))
icon_source = out / "AUTOLEDGER_ICON.png"
icon_source.write_bytes(icon_bytes)

# Use a compact JPEG derivative of the exact user-supplied AutoLedger banner.
# The original full-resolution LOGO remains preserved in the project archive.
logo_source = src / "AUTOLEDGER_LOGO_MODERN_SMALL.jpg"
logo = Image.open(logo_source).convert("RGB")
logo.save(out / "AUTOLEDGER_LOGO_MODERN.png", format="PNG", optimize=True)

icon = Image.open(icon_source).convert("RGBA")
icon_256 = icon.resize((256, 256), Image.Resampling.LANCZOS)
icon_256.save(
    out / "AUTOLEDGER_ICON.ico",
    format="ICO",
    sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(96,96),(128,128),(256,256)],
)
print("Generated AUTOLEDGER supplied LOGO/ICON assets")
