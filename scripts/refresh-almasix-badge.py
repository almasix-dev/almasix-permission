#!/usr/bin/env python3
"""Compose assets/almasix-version-badge.svg from the label plate + live Shields badge."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = ROOT / "assets" / "almasix-badge-label.svg"
OUT = ROOT / "assets" / "almasix-version-badge.svg"
SHIELDS = "https://img.shields.io/pypi/v/almasix?style=for-the-badge&label=&color=4c1d95"


def _dims(svg: str) -> tuple[float, float]:
    match = re.search(r'width="([\d.]+)".*?height="([\d.]+)"', svg)
    if not match:
        raise SystemExit("could not parse svg dimensions")
    return float(match.group(1)), float(match.group(2))


def _inner(svg: str) -> str:
    body = re.sub(r"^<svg[^>]*>\s*", "", svg)
    body = re.sub(r"\s*</svg>\s*$", "", body)
    # Drop nested <title> — the outer badge owns aria labeling.
    return re.sub(r"<title>[^<]*</title>\s*", "", body)


def main() -> None:
    label = LABEL.read_text(encoding="utf-8")
    label_w, label_h = _dims(label)
    req = urllib.request.Request(SHIELDS, headers={"User-Agent": "almasix-permission-badge/1.0"})
    with urllib.request.urlopen(req) as resp:
        value = resp.read().decode("utf-8")
    value_w, value_h = _dims(value)
    title_m = re.search(r"<title>([^<]*)</title>", value)
    version_title = title_m.group(1) if title_m else "almasix"
    total_w = label_w + value_w
    combined = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{label_h}" '
        f'viewBox="0 0 {total_w} {label_h}" role="img" aria-label="Almasix {version_title}">\n'
        f"  <title>Almasix {version_title}</title>\n"
        f'  <svg x="0" y="0" width="{label_w}" height="{label_h}" '
        f'viewBox="0 0 {label_w} {label_h}">\n'
        f"{_inner(label)}\n"
        f"  </svg>\n"
        f'  <svg x="{label_w}" y="0" width="{value_w}" height="{value_h}" '
        f'viewBox="0 0 {value_w} {value_h}">\n'
        f"{_inner(value)}\n"
        f"  </svg>\n"
        f"</svg>\n"
    )
    OUT.write_text(combined, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({total_w}x{label_h}) {version_title}")


if __name__ == "__main__":
    main()
