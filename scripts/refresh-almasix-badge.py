#!/usr/bin/env python3
"""Compose assets/almasix-version-badge.svg from the label plate + supported Almasix range."""

from __future__ import annotations

import re
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = ROOT / "assets" / "almasix-badge-label.svg"
PYPROJECT = ROOT / "pyproject.toml"
OUT = ROOT / "assets" / "almasix-version-badge.svg"
COLOR = "4c1d95"


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


def _almasix_specifier() -> str:
    """Return the Almasix version constraint from project.dependencies (e.g. ``>=0.9.0``)."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    for dep in data.get("project", {}).get("dependencies", []):
        text = str(dep).strip()
        if text == "almasix" or text.startswith("almasix ") or text.startswith("almasix["):
            return "*"
        if text.startswith("almasix"):
            # Strip extras: almasix[foo]>=1.0 → >=1.0
            rest = text[len("almasix") :]
            if rest.startswith("["):
                rest = rest.split("]", 1)[-1]
            return rest.strip() or "*"
    raise SystemExit("almasix dependency not found in pyproject.toml")


def _shields_url(message: str) -> str:
    query = urllib.parse.urlencode(
        {
            "style": "for-the-badge",
            "label": "",
            "message": message,
            "color": COLOR,
        }
    )
    return f"https://img.shields.io/static/v1?{query}"


def main() -> None:
    specifier = _almasix_specifier()
    label = LABEL.read_text(encoding="utf-8")
    label_w, label_h = _dims(label)
    req = urllib.request.Request(
        _shields_url(specifier),
        headers={"User-Agent": "almasix-permission-badge/1.0"},
    )
    with urllib.request.urlopen(req) as resp:
        value = resp.read().decode("utf-8")
    value_w, value_h = _dims(value)
    total_w = label_w + value_w
    combined = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{label_h}" '
        f'viewBox="0 0 {total_w} {label_h}" role="img" '
        f'aria-label="Almasix {specifier}">\n'
        f"  <title>Almasix {specifier}</title>\n"
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
    print(f"wrote {OUT.relative_to(ROOT)} ({total_w}x{label_h}) {specifier}")


if __name__ == "__main__":
    main()
