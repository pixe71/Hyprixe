#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate the original landscape fixtures used by the NixOS session test."""

from pathlib import Path
import sys

from PIL import Image, ImageDraw


def landscape(size, sky, ridges):
    width, height = size
    image = Image.new("RGB", size)
    pen = ImageDraw.Draw(image)
    top, horizon = sky
    for y in range(height):
        rgb = tuple(a + (b - a) * y // (height - 1) for a, b in zip(top, horizon))
        pen.line((0, y, width - 1, y), fill=rgb)
    for color, heights in ridges:
        points = [(i * (width - 1) // (len(heights) - 1), y * height // 100)
                  for i, y in enumerate(heights)]
        pen.polygon([*points, (width - 1, height - 1), (0, height - 1)], fill=color)
    return image


def generate(directory):
    directory.mkdir(parents=True, exist_ok=True)
    amber = landscape(
        (960, 540),
        ((70, 23, 55), (255, 183, 88)),
        [
            ("#e87853", (62, 52, 64, 48, 62, 53, 66)),
            ("#aa4939", (71, 64, 68, 61, 75, 63, 68)),
            ("#612635", (82, 74, 84, 74, 79, 71, 78)),
            ("#351b29", (89, 83, 87, 93, 86, 88, 84)),
        ],
    )
    jade = landscape(
        (800, 600),
        ((29, 88, 84), (149, 240, 175)),
        [
            ("#53b896", (51, 64, 54, 61, 49, 64, 53)),
            ("#268574", (65, 71, 60, 71, 59, 75, 62)),
            ("#205448", (81, 73, 79, 68, 83, 75, 82)),
            ("#17382f", (89, 81, 85, 92, 84, 92, 85)),
        ],
    )
    amber.save(directory / "photo-a.jpg", quality=92, subsampling=0)
    jade.save(directory / "photo-b.png", compress_level=9)


if __name__ == "__main__":
    generate(Path(sys.argv[1]))
