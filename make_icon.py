"""Build a Windows multi-resolution icon from the bundled SOWN logo."""
from pathlib import Path
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
source = HERE / "assets" / "mark.png"
dest = HERE / "assets" / "app.ico"

logo = Image.open(source).convert("RGBA")
canvas = Image.new("RGBA", (1024, 1024), (7, 7, 9, 255))
# Preserve the original full logo, including its lettering and monogram.
logo.thumbnail((856, 856), Image.Resampling.LANCZOS)
canvas.alpha_composite(logo, ((1024 - logo.width) // 2, (1024 - logo.height) // 2))
canvas.save(dest, format="ICO", sizes=[(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)])
print(f"Created {dest} ({dest.stat().st_size} bytes)")
