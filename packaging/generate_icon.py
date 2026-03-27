from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ICO_PATH = ROOT / "assets" / "pikpak_importer_icon.ico"


def rounded_rectangle(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def build_base_image(size: int = 256) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    rounded_rectangle(draw, (20, 20, size - 20, size - 20), 52, fill=(255, 178, 73, 255))
    rounded_rectangle(draw, (54, 84, 202, 184), 20, fill=(255, 248, 231, 245))
    draw.polygon([(54, 115), (202, 115), (202, 100), (182, 84), (130, 84), (114, 68), (74, 68), (54, 84)], fill=(245, 230, 199, 255))

    arrow_color = (32, 116, 151, 255)
    draw.line((138, 129, 164, 155), fill=arrow_color, width=18)
    draw.line((164, 155, 138, 181), fill=arrow_color, width=18)
    draw.line((92, 155, 156, 155), fill=arrow_color, width=18)
    return image


def main() -> int:
    image = build_base_image()
    image.save(
        ICO_PATH,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Generated icon: {ICO_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
