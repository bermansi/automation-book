#!/usr/bin/env python3
"""Generate the seven public Karnaugh maps from their truth-table values.

Every map uses the same variable order, Gray-code columns, line weights, and
two grouping colors. The groups are declared from the minimized expressions,
not copied from movable Word drawing objects.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "source" / "fixed-visuals"
SCALE = 3
ORANGE = "#F58200"
BLUE = "#2F5597"
GRID = "#4B5563"
TEXT = "#111827"


@dataclass(frozen=True)
class MapSpec:
    filename: str
    row_label: str
    column_label: str
    values: tuple[tuple[str, str, str, str], tuple[str, str, str, str]]
    # Each ordinary group is (row_start, row_end, col_start, col_end, color).
    groups: tuple[tuple[int, int, int, int, str], ...]
    # A wrap group joins the first and last columns across the given rows.
    wrap_groups: tuple[tuple[int, int, str], ...] = ()


MAPS = (
    MapSpec(
        "word-fixed-2-1-1-karnaugh.png",
        "TS₁",
        "M₀,Y₀(t)",
        (("0", "1", "1", "1"), ("0", "0", "0", "0")),
        ((0, 0, 1, 2, ORANGE), (0, 0, 2, 3, BLUE)),
    ),
    MapSpec(
        "word-fixed-2-1-2-karnaugh.png",
        "Temp12",
        "Temp18,Y₀(t)",
        (("0", "1", "1", "1"), ("0", "0", "φ", "φ")),
        ((0, 1, 2, 3, ORANGE), (0, 0, 1, 2, BLUE)),
    ),
    MapSpec(
        "word-fixed-2-2-1-fill-karnaugh.png",
        "Y₁(t)",
        "X₂,X₁",
        (("1", "0", "0", "φ"), ("1", "1", "0", "φ")),
        ((1, 1, 0, 1, BLUE),),
        ((0, 1, ORANGE),),
    ),
    MapSpec(
        "word-fixed-2-2-1-drain-karnaugh.png",
        "Y₂(t)",
        "X₂,X₁",
        (("0", "0", "1", "φ"), ("0", "1", "1", "φ")),
        ((0, 1, 2, 3, ORANGE), (1, 1, 1, 2, BLUE)),
    ),
    MapSpec(
        "word-fixed-2-2-1-light-karnaugh.png",
        "X₁",
        "TS₀,Y₃(t)",
        (("0", "1", "0", "0"), ("1", "1", "1", "1")),
        ((1, 1, 0, 3, ORANGE), (0, 1, 1, 1, BLUE)),
    ),
    MapSpec(
        "word-fixed-2-2-2-karnaugh.png",
        "M₀",
        "TS₀,Y₀(t)",
        (("0", "1", "0", "0"), ("1", "1", "1", "1")),
        ((1, 1, 0, 3, ORANGE), (0, 1, 1, 1, BLUE)),
    ),
    MapSpec(
        "word-fixed-2-2-3-karnaugh.png",
        "M₁",
        "M₂,Y₁(t)",
        (("0", "1", "1", "1"), ("0", "0", "0", "0")),
        ((0, 0, 1, 2, ORANGE), (0, 0, 2, 3, BLUE)),
    ),
)


def font(size: int, italic: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Oblique.ttf"
        if italic
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    )
    path = next(Path(item) for item in candidates if Path(item).exists())
    return ImageFont.truetype(str(path), size * SCALE)


def centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], value: str, face) -> None:
    left, top, right, bottom = box
    bounds = draw.textbbox((0, 0), value, font=face)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    draw.text(
        ((left + right - width) / 2, (top + bottom - height) / 2 - bounds[1]),
        value,
        font=face,
        fill=TEXT,
    )


def render(spec: MapSpec) -> None:
    for row_start, row_end, col_start, col_end, _ in spec.groups:
        cells = [
            spec.values[row][column]
            for row in range(row_start, row_end + 1)
            for column in range(col_start, col_end + 1)
        ]
        if len(cells) not in {1, 2, 4, 8} or any(value not in {"1", "φ"} for value in cells):
            raise ValueError(f"Invalid Karnaugh group in {spec.filename}: {cells}")
    for row_start, row_end, _ in spec.wrap_groups:
        cells = [
            spec.values[row][column]
            for row in range(row_start, row_end + 1)
            for column in (0, 3)
        ]
        if len(cells) not in {2, 4} or any(value not in {"1", "φ"} for value in cells):
            raise ValueError(f"Invalid wrap group in {spec.filename}: {cells}")

    width, height = 1000, 310
    image = Image.new("RGB", (width * SCALE, height * SCALE), "white")
    draw = ImageDraw.Draw(image)
    normal = font(28)
    small = font(23)
    italic = font(24, italic=True)

    x0, y0 = 64 * SCALE, 35 * SCALE
    label_width, cell_width = 250 * SCALE, 166 * SCALE
    header_height, row_height = 82 * SCALE, 86 * SCALE
    x_edges = [x0, x0 + label_width] + [
        x0 + label_width + cell_width * index for index in range(1, 5)
    ]
    y_edges = [y0, y0 + header_height, y0 + header_height + row_height, y0 + header_height + 2 * row_height]

    for x in x_edges:
        draw.line((x, y_edges[0], x, y_edges[-1]), fill=GRID, width=2 * SCALE)
    for y in y_edges:
        draw.line((x_edges[0], y, x_edges[-1], y), fill=GRID, width=2 * SCALE)

    centered(draw, (x_edges[0], y_edges[0], x_edges[1], y_edges[1]), f"{spec.row_label} \\ {spec.column_label}", italic)
    for column, gray in enumerate(("00", "01", "11", "10")):
        centered(draw, (x_edges[column + 1], y_edges[0], x_edges[column + 2], y_edges[1]), gray, normal)
    for row, label in enumerate(("0", "1")):
        centered(draw, (x_edges[0], y_edges[row + 1], x_edges[1], y_edges[row + 2]), label, normal)
        for column, value in enumerate(spec.values[row]):
            centered(
                draw,
                (x_edges[column + 1], y_edges[row + 1], x_edges[column + 2], y_edges[row + 2]),
                value,
                small,
            )

    pad_x, pad_y = 12 * SCALE, 12 * SCALE
    for row_start, row_end, col_start, col_end, color in spec.groups:
        box = (
            x_edges[col_start + 1] + pad_x,
            y_edges[row_start + 1] + pad_y,
            x_edges[col_end + 2] - pad_x,
            y_edges[row_end + 2] - pad_y,
        )
        draw.rounded_rectangle(box, radius=34 * SCALE, outline=color, width=5 * SCALE)

    for row_start, row_end, color in spec.wrap_groups:
        # The two same-colored edge loops denote one wrap-around group.
        for column in (0, 3):
            box = (
                x_edges[column + 1] + pad_x,
                y_edges[row_start + 1] + pad_y,
                x_edges[column + 2] - pad_x,
                y_edges[row_end + 2] - pad_y,
            )
            draw.rounded_rectangle(box, radius=34 * SCALE, outline=color, width=5 * SCALE)

    image = image.resize((width, height), Image.Resampling.LANCZOS)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT / spec.filename, "PNG", optimize=True)


for map_spec in MAPS:
    render(map_spec)
