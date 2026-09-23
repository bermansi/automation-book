#!/usr/bin/env python3
"""Remove the dark editor canvas from the two authoritative Arduino figures.

The diagrams themselves use true black lines. The editor canvas is a distinct
dark gray (RGB 38,38,38), so it can be replaced deterministically without
altering the circuit. The button label is redrawn in black because it was
originally white text on that dark canvas.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
FIXED = ROOT / "source" / "fixed-visuals"


def remove_editor_canvas(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGB")
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            # The editor canvas and its antialiasing are neutral dark grays.
            # Preserve true-black circuit lines and all colored wiring.
            if 18 <= red <= 48 and abs(red - green) <= 2 and abs(green - blue) <= 2:
                pixels[x, y] = (255, 255, 255)
    return image


button_path = FIXED / "word-fixed-5-5-button.png"
button = remove_editor_canvas(button_path)

# Clear the original white-on-dark label and place it back as black-on-white.
draw = ImageDraw.Draw(button)
draw.rectangle((220, 169, 294, 204), fill="white")
font_candidates = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]
font_path = next((path for path in font_candidates if Path(path).exists()), None)
font = ImageFont.truetype(font_path, 18) if font_path else ImageFont.load_default()
label = "Button"
box = draw.textbbox((0, 0), label, font=font)
label_width = box[2] - box[0]
draw.text(((517 - label_width) / 2, 174), label, fill="black", font=font)
button.save(button_path)

circuit_path = FIXED / "word-fixed-5-5-circuit.png"
remove_editor_canvas(circuit_path).save(circuit_path)
