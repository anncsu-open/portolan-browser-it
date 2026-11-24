# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Apply this repository's overlay to a checkout of the Portolan Browser.

Usage:
    uv run scripts/apply_overlay.py <browser_root> [--overlay <overlay_root>]

The overlay extends browser files instead of copying them, so an upstream
release keeps its own changes: SCSS is appended after a marker, locale JSON
is merged, `index.html` is edited at exact anchors. The only file replaced is
`widgets.config.js`, and only while upstream ships it empty. Every check runs
before anything is written, so a moved anchor stops the build and leaves the
checkout untouched.
"""

import argparse
import json
import re
import shutil
from pathlib import Path

MARKER = "// portolan-browser-it overlay: {source}"
EMPTY_WIDGETS = "import{defineAsyncComponent}from'vue';exportdefault{};"

# Bootstrap computes its colour maps when variables.scss imports it, so the
# tokens must be set before that line; appending them would change nothing.
INSERTS_BEFORE = [
    (
        "theme/variables-it-before.scss",
        "src/theme/variables.scss",
        "@import 'bootstrap/scss/_variables';",
    ),
]
APPENDS = [
    ("theme/variables-it.scss", "src/theme/variables.scss"),
    ("theme/custom-it.scss", "src/theme/custom.scss"),
]
# SCSS files whose variables must already exist upstream. A name the browser
# renamed would otherwise be set here and read nowhere. Names starting with
# `it-` are our own.
VARIABLE_SOURCES = ["theme/variables-it-before.scss", "theme/variables-it.scss"]
VARIABLE_TARGET = "src/theme/variables.scss"
# Bootstrap's own variables, which carry !default and can be set before the
# browser imports them. The file exists once the checkout is installed.
BOOTSTRAP_VARIABLES = "node_modules/bootstrap/scss/_variables.scss"
OWN_VARIABLE_PREFIX = "it-"
ASSIGNMENT = re.compile(r"^\s*\$([\w-]+)\s*:", re.MULTILINE)
# Locale keys under these top-level groups are our own labels.
OWN_LOCALE_GROUPS = {"footerLinks"}
ENGLISH_TEXTS = "src/locales/en/texts.json"
LOCALES = [
    ("locales/it/custom.json", "src/locales/it/custom.json"),
    ("locales/en/custom.json", "src/locales/en/custom.json"),
]
INDEX_REPLACEMENTS = [
    ('<html lang="en">', '<html lang="it">'),
    (
        '<link rel="icon" type="image/svg+xml" href="/portolan-logo.svg">',
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg">',
    ),
    ("</head>", '  <link rel="stylesheet" href="/fonts.css">\n  </head>'),
]
# Lines dropped whole, matched by their start once stripped: no request
# leaves for Google Fonts, the fonts come from public/fonts.css.
INDEX_REMOVED_LINES = [
    '<link rel="preconnect" href="https://fonts.googleapis.com">',
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
    '<link href="https://fonts.googleapis.com/css2?',
]


class OverlayError(Exception):
    """The browser checkout does not look like the one the overlay expects."""


def _read(path: Path) -> str:
    if not path.is_file():
        raise OverlayError(f"{path} is missing in the browser checkout")
    return path.read_text(encoding="utf-8")


def _source(overlay_root: Path, relative: str) -> Path:
    path = overlay_root / relative
    if not path.exists():
        raise OverlayError(f"{relative} is missing in the overlay")
    return path


def _leaf_keys(data: dict, prefix: str = "") -> set[str]:
    keys = set()
    for key, value in data.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys |= _leaf_keys(value, dotted)
        else:
            keys.add(dotted)
    return keys


def _check_variables(overlay_root: Path, browser_root: Path) -> None:
    upstream = set(ASSIGNMENT.findall(_read(browser_root / VARIABLE_TARGET)))
    bootstrap = browser_root / BOOTSTRAP_VARIABLES
    if bootstrap.is_file():
        upstream |= set(ASSIGNMENT.findall(bootstrap.read_text(encoding="utf-8")))
    for source in VARIABLE_SOURCES:
        ours = ASSIGNMENT.findall(_source(overlay_root, source).read_text(encoding="utf-8"))
        unknown = sorted(
            name
            for name in set(ours)
            if not name.startswith(OWN_VARIABLE_PREFIX) and name not in upstream
        )
        if unknown:
            raise OverlayError(
                f"{source} sets variables that neither {VARIABLE_TARGET} nor "
                f"Bootstrap's {BOOTSTRAP_VARIABLES} declares: "
                + ", ".join(f"${name}" for name in unknown)
            )


def _check_locale_keys(ours: dict, upstream_custom: dict, english: dict, source: str) -> None:
    known = _leaf_keys(english) | _leaf_keys(upstream_custom)
    unknown = sorted(
        key
        for key in _leaf_keys(ours)
        if key.split(".", 1)[0] not in OWN_LOCALE_GROUPS and key not in known
    )
    if unknown:
        raise OverlayError(
            f"{source} translates keys the browser no longer has: " + ", ".join(unknown)
        )


def _deep_merge(base: dict, ours: dict) -> dict:
    merged = dict(base)
    for key, value in ours.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _edit_index(html: str, path: Path) -> str:
    for anchor, replacement in INDEX_REPLACEMENTS:
        count = html.count(anchor)
        if count != 1:
            raise OverlayError(
                f"{path}: expected the anchor {anchor!r} once, found it {count} times"
            )
        html = html.replace(anchor, replacement)
    lines = html.splitlines(keepends=True)
    for anchor in INDEX_REMOVED_LINES:
        matches = [i for i, line in enumerate(lines) if line.strip().startswith(anchor)]
        if len(matches) != 1:
            raise OverlayError(
                f"{path}: expected one line starting with the anchor {anchor!r}, "
                f"found {len(matches)}"
            )
        del lines[matches[0]]
    return "".join(lines)


def apply(overlay_root: Path, browser_root: Path) -> None:
    """Extend the browser checkout with the overlay, or change nothing."""
    writes: dict[Path, str] = {}
    _check_variables(overlay_root, browser_root)

    for source, target, anchor in INSERTS_BEFORE:
        src = _source(overlay_root, source)
        dst = browser_root / target
        current = writes.get(dst) or _read(dst)
        marker = MARKER.format(source=source)
        if marker in current:
            raise OverlayError(f"{dst}: the overlay is already applied")
        if current.count(anchor) != 1:
            raise OverlayError(
                f"{dst}: expected the anchor {anchor!r} once, "
                f"found it {current.count(anchor)} times"
            )
        block = f"{marker}\n{src.read_text(encoding='utf-8').rstrip()}\n\n"
        writes[dst] = current.replace(anchor, block + anchor)

    for source, target in APPENDS:
        src = _source(overlay_root, source)
        dst = browser_root / target
        current = writes.get(dst) or _read(dst)
        marker = MARKER.format(source=source)
        if marker in current:
            raise OverlayError(f"{dst}: the overlay is already applied")
        writes[dst] = (
            f"{current.rstrip()}\n\n{marker}\n{src.read_text(encoding='utf-8')}"
        )

    english = json.loads(_read(browser_root / ENGLISH_TEXTS))
    for source, target in LOCALES:
        src = _source(overlay_root, source)
        dst = browser_root / target
        upstream_custom = json.loads(_read(dst))
        ours = json.loads(src.read_text(encoding="utf-8"))
        _check_locale_keys(ours, upstream_custom, english, source)
        merged = _deep_merge(upstream_custom, ours)
        writes[dst] = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"

    widgets_src = _source(overlay_root, "widgets.config.js")
    widgets_dst = browser_root / "widgets.config.js"
    if "".join(_read(widgets_dst).split()) != EMPTY_WIDGETS:
        raise OverlayError(
            f"{widgets_dst} is no longer empty upstream; merge it by hand "
            "instead of replacing it"
        )
    writes[widgets_dst] = widgets_src.read_text(encoding="utf-8")

    index = browser_root / "index.html"
    writes[index] = _edit_index(_read(index), index)
    public = _source(overlay_root, "public")

    for path, text in writes.items():
        path.write_text(text, encoding="utf-8")

    shutil.copytree(public, browser_root / "public", dirs_exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("browser_root", type=Path)
    parser.add_argument(
        "--overlay", type=Path, default=Path(__file__).resolve().parent.parent
    )
    args = parser.parse_args()
    apply(args.overlay, args.browser_root)
    print(f"Overlay applied to {args.browser_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
