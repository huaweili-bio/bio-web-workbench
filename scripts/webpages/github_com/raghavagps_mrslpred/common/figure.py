from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor, ImageDraw, ImageFont


DEFAULT_TITLE = "mRNA subcellular localization prediction (MRSLpred)"
DEFAULT_PREDICTED_COLOR = "#3E8FB0"
DEFAULT_UNPREDICTED_COLOR = "#ECECEC"
DEFAULT_BACKGROUND_COLOR = "#FFFFFF"
DEFAULT_YES_TEXT_COLOR = "#FFFFFF"
DEFAULT_NO_TEXT_COLOR = "#9B9B9B"
DEFAULT_LABEL_TEXT_COLOR = "#111111"
DEFAULT_LEGEND_TEXT_COLOR = "#222222"
LOCALIZATION_COLUMNS = [("ribosome_label", "Ribosome"), ("cytosol_label", "Cytosol"), ("er_label", "ER"), ("membrane_label", "Membrane"), ("nucleus_label", "Nucleus"), ("exosome_label", "Exosome")]
REQUIRED_COLUMNS = ["gene_symbol", "transcript_accession_version"] + [field for field, _ in LOCALIZATION_COLUMNS]


class MrslpredFigureError(RuntimeError):
    """Raised when the figure task cannot parse or render the input result."""


def safe_filename(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    sanitized = sanitized.strip("._")
    return sanitized or "job"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_result_input_artifacts(*, input_path: Path, temp_dir: Path | None) -> dict[str, str]:
    metadata = {"original_input_file": "", "copied_input_file": ""}
    if temp_dir is None:
        return metadata
    temp_dir.mkdir(parents=True, exist_ok=True)
    copied_input = temp_dir / f"original_input{input_path.suffix or '.csv'}"
    shutil.copyfile(input_path, copied_input)
    metadata["original_input_file"] = str(input_path)
    metadata["copied_input_file"] = str(copied_input)
    return metadata


def load_result_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise MrslpredFigureError(f"Input result is missing required columns: {', '.join(missing)}")
        rows = [{str(key): str(value or "") for key, value in row.items()} for row in reader]
    if not rows:
        raise MrslpredFigureError(f"No rows were found in: {path}")
    return rows


def _font_candidates(name: str) -> list[Path]:
    windows_font_dir = Path("C:/Windows/Fonts")
    mapping = {
        "title": ["arialbd.ttf", "seguisb.ttf"],
        "gene": ["arialbi.ttf", "timesbi.ttf", "arialbd.ttf"],
        "transcript": ["arial.ttf", "calibri.ttf"],
        "cell": ["arialbd.ttf", "seguisb.ttf"],
        "axis": ["arialbd.ttf", "seguisb.ttf"],
        "legend": ["arial.ttf", "calibri.ttf"],
    }
    return [windows_font_dir / item for item in mapping.get(name, [])]


def load_font(kind: str, size: int) -> ImageFont.ImageFont:
    for candidate in _font_candidates(kind):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def render_localization_figure(*, rows: list[dict[str, str]], output_path: Path, title: str) -> dict[str, Any]:
    predicted_color = ImageColor.getrgb(DEFAULT_PREDICTED_COLOR)
    unpredicted_color = ImageColor.getrgb(DEFAULT_UNPREDICTED_COLOR)
    background_color = ImageColor.getrgb(DEFAULT_BACKGROUND_COLOR)
    yes_text_color = ImageColor.getrgb(DEFAULT_YES_TEXT_COLOR)
    no_text_color = ImageColor.getrgb(DEFAULT_NO_TEXT_COLOR)
    label_text_color = ImageColor.getrgb(DEFAULT_LABEL_TEXT_COLOR)
    legend_text_color = ImageColor.getrgb(DEFAULT_LEGEND_TEXT_COLOR)
    title_font = load_font("title", 46)
    gene_font = load_font("gene", 34)
    transcript_font = load_font("transcript", 21)
    cell_font = load_font("cell", 28)
    axis_font = load_font("axis", 28)
    legend_font = load_font("legend", 24)
    row_count = len(rows)
    col_count = len(LOCALIZATION_COLUMNS)
    left_margin, right_margin, top_margin, title_height = 60, 60, 30, 100
    grid_top, label_area_width, cell_width, cell_height = top_margin + title_height, 260, 200, 130
    col_gap, row_gap, x_label_height, legend_height, bottom_margin, radius = 20, 28, 90, 85, 35, 12
    width = left_margin + label_area_width + (col_count * cell_width) + ((col_count - 1) * col_gap) + right_margin
    grid_height = (row_count * cell_height) + ((row_count - 1) * row_gap)
    height = grid_top + grid_height + x_label_height + legend_height + bottom_margin
    image = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(image)
    title_width, _ = text_bbox(draw, title, title_font)
    draw.text(((width - title_width) / 2, top_margin), title, fill=label_text_color, font=title_font)
    grid_left = left_margin + label_area_width
    grid_bottom = grid_top + grid_height
    for row_index, row in enumerate(rows):
        y0 = grid_top + row_index * (cell_height + row_gap)
        gene_text = str(row["gene_symbol"]).strip()
        transcript_text = f"({str(row['transcript_accession_version']).strip()})"
        _, gene_height = text_bbox(draw, gene_text, gene_font)
        _, transcript_height = text_bbox(draw, transcript_text, transcript_font)
        label_total_height = gene_height + 8 + transcript_height
        label_y = y0 + (cell_height - label_total_height) / 2
        draw.text((left_margin, label_y), gene_text, fill=label_text_color, font=gene_font)
        draw.text((left_margin, label_y + gene_height + 8), transcript_text, fill=label_text_color, font=transcript_font)
        for col_index, (field_name, _) in enumerate(LOCALIZATION_COLUMNS):
            x0 = grid_left + col_index * (cell_width + col_gap)
            x1 = x0 + cell_width
            value = str(row.get(field_name, "")).strip()
            is_yes = value == "Yes"
            box_color = predicted_color if is_yes else unpredicted_color
            text_color = yes_text_color if is_yes else no_text_color
            draw.rounded_rectangle((x0, y0, x1, y0 + cell_height), radius=radius, fill=box_color)
            label = "Yes" if is_yes else "No"
            text_width, text_height = text_bbox(draw, label, cell_font)
            draw.text((x0 + (cell_width - text_width) / 2, y0 + (cell_height - text_height) / 2 - 3), label, fill=text_color, font=cell_font)
    x_label_top = grid_bottom + 24
    for col_index, (_, display_name) in enumerate(LOCALIZATION_COLUMNS):
        x0 = grid_left + col_index * (cell_width + col_gap)
        label_width, _ = text_bbox(draw, display_name, axis_font)
        draw.text((x0 + (cell_width - label_width) / 2, x_label_top), display_name, fill=label_text_color, font=axis_font)
    legend_top = x_label_top + x_label_height - 10
    legend_box, legend_gap, legend_text_gap = 36, 18, 16
    predicted_label, unpredicted_label = "Predicted localization", "Not predicted"
    predicted_text_width, _ = text_bbox(draw, predicted_label, legend_font)
    unpredicted_text_width, _ = text_bbox(draw, unpredicted_label, legend_font)
    legend_width = legend_box + legend_text_gap + predicted_text_width + legend_gap * 2 + legend_box + legend_text_gap + unpredicted_text_width
    legend_left = (width - legend_width) / 2
    draw.rectangle((legend_left, legend_top, legend_left + legend_box, legend_top + legend_box), fill=predicted_color)
    draw.text((legend_left + legend_box + legend_text_gap, legend_top + 2), predicted_label, fill=legend_text_color, font=legend_font)
    second_box_left = legend_left + legend_box + legend_text_gap + predicted_text_width + legend_gap * 2
    draw.rectangle((second_box_left, legend_top, second_box_left + legend_box, legend_top + legend_box), fill=unpredicted_color)
    draw.text((second_box_left + legend_box + legend_text_gap, legend_top + 2), unpredicted_label, fill=legend_text_color, font=legend_font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return {"width_px": width, "height_px": height, "row_count": row_count, "column_count": col_count, "predicted_color": DEFAULT_PREDICTED_COLOR, "unpredicted_color": DEFAULT_UNPREDICTED_COLOR}


def build_figure_summary_result(rows: list[dict[str, str]]) -> dict[str, Any]:
    labels = [display_name for _, display_name in LOCALIZATION_COLUMNS]
    return {
        "row_order": [
            {
                "gene_symbol": row["gene_symbol"],
                "transcript_accession_version": row["transcript_accession_version"],
                "predicted_locations": [label for field, label in LOCALIZATION_COLUMNS if row[field] == "Yes"],
            }
            for row in rows
        ],
        "columns": labels,
    }
