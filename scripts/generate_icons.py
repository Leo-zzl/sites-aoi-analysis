"""Generate Electron app icons for Windows (.ico) and macOS (.icns)."""

import struct
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).parent.parent / "electron" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

ICO_SIZES = [16, 32, 48, 64, 128, 256]
ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def draw_icon(size: int) -> Image.Image:
    """Render a simple map-pin + tower icon at the given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size // 16
    bbox = [margin, margin, size - margin, size - margin]
    draw.ellipse(bbox, fill="#2563EB")

    inner_margin = size // 8
    inner_bbox = [inner_margin, inner_margin, size - inner_margin, size - inner_margin]
    draw.ellipse(inner_bbox, fill="#3B82F6")

    cx, cy = size // 2, size // 2
    line_w = max(1, size // 32)
    pin_h = size // 3
    pin_w = size // 5

    top_y = cy - pin_h // 2
    bot_y = cy + pin_h // 2
    left_x = cx - pin_w // 2
    right_x = cx + pin_w // 2

    draw.polygon(
        [(cx, bot_y), (left_x, top_y), (right_x, top_y)],
        fill="white",
    )

    draw.line([(cx, top_y - pin_h // 4), (cx, bot_y)], fill="white", width=line_w)

    arc_r = pin_w // 3
    for i in range(1, 4):
        r = arc_r * i
        draw.arc(
            [cx - r, top_y - r - pin_h // 6, cx + r, top_y + r - pin_h // 6],
            start=200,
            end=340,
            fill="white",
            width=line_w,
        )

    return img


def build_ico(images: list[Image.Image]) -> bytes:
    """Manually construct a multi-resolution ICO file from PNG data."""
    num_images = len(images)
    header = struct.pack("<HHH", 0, 1, num_images)

    # Directory size: 16 bytes per entry
    dir_size = 16 * num_images
    data_offset = 6 + dir_size

    directory = b""
    image_data = b""

    for img in images:
        size = img.width
        # Save as PNG (required for 256x256, also works for smaller)
        buf = BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        # ICO directory entry
        # Width/Height: 0 means 256
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        directory += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png_bytes), data_offset)
        image_data += png_bytes
        data_offset += len(png_bytes)

    return header + directory + image_data


def generate_ico():
    images = [draw_icon(s).convert("RGBA") for s in ICO_SIZES]
    ico_path = ASSETS_DIR / "icon.ico"
    ico_path.write_bytes(build_ico(images))
    print(f"Generated {ico_path} ({len(ICO_SIZES)} sizes)")


def generate_icns():
    images = [draw_icon(s).convert("RGBA") for s in ICNS_SIZES]
    icns_path = ASSETS_DIR / "icon.icns"
    images[0].save(
        icns_path,
        format="ICNS",
        append_images=images[1:],
    )
    print(f"Generated {icns_path}")


if __name__ == "__main__":
    generate_ico()
    generate_icns()
