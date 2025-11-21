#!/usr/bin/env python3
"""Utility script for preparing LoRA training datasets.

The script assumes the following scenario:
* Raw (possibly alpha matted) images live under `data-source/picture`.
* Caption text files may exist alongside the images; otherwise the script
  creates fallback captions based on CLI arguments.
* Output is structured for sd-scripts / kohya_ss training, e.g.
      train_data/
        yokai_style/
          00001.png
          00001.txt

Features:
* Alpha channel removal with configurable solid background colours.
* Optional longest-side down-scaling to keep memory use predictable.
* Automatic caption file generation with trigger words & folder tags.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image


DEFAULT_INPUT = Path(__file__).resolve().parent / "data-source" / "picture"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "prepared-dataset"


def parse_background(color: str) -> tuple[int, int, int]:
    """Parse hex (#RRGGBB) or comma separated `r,g,b` values."""
    color = color.strip()
    if color.startswith("#"):
        color = color.lstrip("#")
        if len(color) != 6:
            raise ValueError("Hex colours must be 6 characters, e.g. #ffffff")
        return tuple(int(color[i : i + 2], 16) for i in range(0, 6, 2))  # type: ignore[return-value]
    parts = color.split(",")
    if len(parts) != 3:
        raise ValueError("RGB colours must have three comma-separated values")
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


@dataclass
class PrepConfig:
    input_dir: Path
    output_dir: Path
    background: tuple[int, int, int]
    max_side: int | None
    default_trigger: str
    use_folder_name: bool
    preserve_subdirs: bool
    image_exts: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp")


def iter_images(root: Path, exts: Iterable[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.suffix.lower() in exts and path.is_file():
            yield path


def ensure_alpha_removed(img: Image.Image, bg: tuple[int, int, int]) -> Image.Image:
    if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
        logging.debug("Applying background for alpha image")
        canvas = Image.new("RGBA", img.size, bg + (255,))
        canvas.paste(img, mask=img.getchannel("A") if img.mode == "RGBA" else img.convert("RGBA"))
        img = canvas.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img


def resize_long_side(img: Image.Image, max_side: int) -> Image.Image:
    if max_side is None or max_side <= 0:
        return img
    w, h = img.size
    largest = max(w, h)
    if largest <= max_side:
        return img
    scale = max_side / largest
    new_size = (int(w * scale), int(h * scale))
    logging.debug("Resizing %s -> %s", (w, h), new_size)
    return img.resize(new_size, Image.Resampling.LANCZOS)


def build_caption(img_path: Path, cfg: PrepConfig) -> str:
    caption_path = img_path.with_suffix(".txt")
    if caption_path.exists():
        return caption_path.read_text(encoding="utf-8").strip()

    tags: list[str] = []
    if cfg.default_trigger:
        tags.append(cfg.default_trigger)
    if cfg.use_folder_name:
        tags.append(img_path.parent.name)
    tags.append(img_path.stem.replace("_", " "))
    return ", ".join(tag for tag in tags if tag)


def relative_output_path(src: Path, cfg: PrepConfig) -> Path:
    if cfg.preserve_subdirs:
        rel = src.relative_to(cfg.input_dir)
        return cfg.output_dir / rel.parent
    return cfg.output_dir


def process_image(path: Path, cfg: PrepConfig) -> None:
    out_dir = relative_output_path(path, cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_stem = out_dir / path.stem

    with Image.open(path) as img:
        img = ensure_alpha_removed(img, cfg.background)
        img = resize_long_side(img, cfg.max_side) if cfg.max_side else img
        out_path = out_stem.with_suffix(".png")
        img.save(out_path, format="PNG", optimize=True)

    caption = build_caption(path, cfg)
    (out_stem.with_suffix(".txt")).write_text(caption + "\n", encoding="utf-8")
    logging.info("Prepared %s -> %s", path, out_stem.with_suffix(".png"))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare LoRA training dataset.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT, help="Directory with raw images")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT, help="Where processed data will be stored")
    parser.add_argument(
        "--background",
        type=parse_background,
        default="#ffffff",
        help="Background colour for transparent pixels (hex or r,g,b)",
    )
    parser.add_argument(
        "--max-side",
        type=int,
        default=1024,
        help="Resize so the longest side equals this value (0 to disable)",
    )
    parser.add_argument(
        "--default-trigger",
        type=str,
        default="yokai style",
        help="Primary tag/training trigger inserted when caption is missing",
    )
    parser.add_argument(
        "--use-folder-name",
        action="store_true",
        help="Append the immediate folder name to auto-generated captions",
    )
    parser.add_argument(
        "--preserve-subdirs",
        action="store_true",
        help="Keep the original folder hierarchy under the output directory",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))

    cfg = PrepConfig(
        input_dir=args.input_dir.expanduser(),
        output_dir=args.output_dir.expanduser(),
        background=args.background,
        max_side=None if args.max_side <= 0 else args.max_side,
        default_trigger=args.default_trigger.strip(),
        use_folder_name=args.use_folder_name,
        preserve_subdirs=args.preserve_subdirs,
    )

    if not cfg.input_dir.exists():
        logging.error("Input directory %s does not exist", cfg.input_dir)
        return 1

    files = list(iter_images(cfg.input_dir, cfg.image_exts))
    if not files:
        logging.warning("No images found under %s", cfg.input_dir)
        return 0

    logging.info("Preparing %d images", len(files))
    for img_path in files:
        try:
            process_image(img_path, cfg)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed to process %s: %s", img_path, exc)
    logging.info("Dataset ready in %s", cfg.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

