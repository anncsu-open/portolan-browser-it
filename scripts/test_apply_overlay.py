# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest",
# ]
# ///
"""Tests for apply_overlay.py.

Usage:
    uv run scripts/test_apply_overlay.py
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from apply_overlay import OverlayError, apply

ROOT = Path(__file__).resolve().parent.parent
MINI = ROOT / "tests" / "fixtures" / "browser-mini"
EMPTY_WIDGETS = "import { defineAsyncComponent } from 'vue';\n\nexport default {};\n"


@pytest.fixture
def browser(tmp_path) -> Path:
    target = tmp_path / "browser"
    shutil.copytree(MINI, target)
    return target


@pytest.fixture
def overlay(tmp_path) -> Path:
    root = tmp_path / "overlay"
    (root / "theme").mkdir(parents=True)
    (root / "theme" / "variables-it.scss").write_text("$header: #0066cc;\n")
    (root / "theme" / "variables-it-before.scss").write_text("$primary: #0066cc;\n")
    (root / "theme" / "custom-it.scss").write_text(".it-slim { color: white; }\n")
    for lang, label in (("it", "Cataloghi"), ("en", "Catalogs")):
        (root / "locales" / lang).mkdir(parents=True)
        (root / "locales" / lang / "custom.json").write_text(
            json.dumps(
                {
                    "index": {"selectFromRegistry": label},
                    "footerLinks": {"legal": f"{label} legal"},
                }
            )
        )
    (root / "widgets.config.js").write_text("export default { 'root-start': [] };\n")
    (root / "public" / "fonts").mkdir(parents=True)
    (root / "public" / "fonts.css").write_text("/* fonts */\n")
    (root / "public" / "fonts" / "a.woff2").write_bytes(b"woff2")
    return root


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_appends_theme_files_after_a_marker(overlay, browser):
    apply(overlay, browser)
    after = read(browser / "src/theme/variables.scss")
    last_upstream_line = "@import 'bootstrap/scss/_variables-dark';"
    tail = after[after.index(last_upstream_line) :]
    assert "portolan-browser-it overlay: theme/variables-it.scss" in tail
    assert after.rstrip().endswith("$header: #0066cc;")
    assert (
        read(browser / "src/theme/custom.scss")
        .rstrip()
        .endswith(".it-slim { color: white; }")
    )


def test_inserts_tokens_before_the_bootstrap_import(overlay, browser):
    apply(overlay, browser)
    scss = read(browser / "src/theme/variables.scss")
    ours = scss.index("$primary: #0066cc;")
    assert ours > scss.index("$primary:   #4163cc;")
    assert ours < scss.index("@import 'bootstrap/scss/_variables';")


def test_missing_bootstrap_import_fails(overlay, browser):
    path = browser / "src/theme/variables.scss"
    path.write_text(read(path).replace("@import 'bootstrap/scss/_variables';", ""))
    with pytest.raises(OverlayError, match="bootstrap/scss/_variables"):
        apply(overlay, browser)


def test_applying_twice_fails(overlay, browser):
    apply(overlay, browser)
    with pytest.raises(OverlayError, match="already"):
        apply(overlay, browser)


def test_merges_locale_json_keeping_upstream_keys(overlay, browser):
    apply(overlay, browser)
    merged = json.loads(read(browser / "src/locales/it/custom.json"))
    assert merged["fields"] == {}
    assert merged["authConfig"] == {"description": ""}
    assert merged["index"]["selectFromRegistry"] == "Cataloghi"
    assert merged["footerLinks"]["legal"] == "Cataloghi legal"
    english = json.loads(read(browser / "src/locales/en/custom.json"))
    assert english["index"]["selectFromRegistry"] == "Catalogs"


def test_ours_wins_on_conflicting_keys(overlay, browser):
    (overlay / "locales" / "it" / "custom.json").write_text(
        json.dumps({"authConfig": {"description": "nostra"}})
    )
    apply(overlay, browser)
    merged = json.loads(read(browser / "src/locales/it/custom.json"))
    assert merged["authConfig"]["description"] == "nostra"


def test_replaces_the_empty_widgets_config(overlay, browser):
    apply(overlay, browser)
    assert read(browser / "widgets.config.js") == read(overlay / "widgets.config.js")


def test_refuses_a_non_empty_widgets_config(overlay, browser):
    (browser / "widgets.config.js").write_text("export default { 'x': [1] };\n")
    with pytest.raises(OverlayError, match="widgets.config.js"):
        apply(overlay, browser)


def test_copies_public_files(overlay, browser):
    apply(overlay, browser)
    assert (browser / "public" / "fonts.css").exists()
    assert (browser / "public" / "fonts" / "a.woff2").read_bytes() == b"woff2"
    assert (browser / "public" / "portolan-logo.svg").exists()


def test_edits_index_html(overlay, browser):
    apply(overlay, browser)
    html = read(browser / "index.html")
    assert '<html lang="it">' in html and '<html lang="en">' not in html
    assert "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html
    assert 'href="/favicon.svg"' in html and "portolan-logo.svg" not in html
    assert html.index('<link rel="stylesheet" href="/fonts.css">') < html.index(
        "</head>"
    )


@pytest.mark.parametrize(
    "anchor",
    [
        '<html lang="en">',
        '<link rel="icon" type="image/svg+xml" href="/portolan-logo.svg">',
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        "</head>",
    ],
)
def test_missing_anchor_names_the_file_and_the_anchor(overlay, browser, anchor):
    html = browser / "index.html"
    html.write_text(read(html).replace(anchor, ""))
    with pytest.raises(OverlayError) as error:
        apply(overlay, browser)
    assert "index.html" in str(error.value) and anchor in str(error.value)


def test_missing_target_file_fails(overlay, browser):
    (browser / "src" / "theme" / "custom.scss").unlink()
    with pytest.raises(OverlayError, match="custom.scss"):
        apply(overlay, browser)


def test_missing_overlay_source_fails(overlay, browser):
    shutil.rmtree(overlay / "locales")
    with pytest.raises(OverlayError, match="locales/it/custom.json"):
        apply(overlay, browser)


def test_unknown_scss_variable_fails(overlay, browser):
    # A variable renamed upstream would leave ours unused and the theme half done.
    (overlay / "theme" / "variables-it.scss").write_text("$no-such-variable: 1px;\n")
    with pytest.raises(OverlayError, match="no-such-variable"):
        apply(overlay, browser)


def test_it_prefixed_variables_are_ours(overlay, browser):
    (overlay / "theme" / "variables-it.scss").write_text("$it-slim-background: #000;\n")
    apply(overlay, browser)


def write_bootstrap_variables(browser: Path) -> None:
    # Bootstrap's own variables, present once the checkout is installed.
    path = browser / "node_modules" / "bootstrap" / "scss" / "_variables.scss"
    path.parent.mkdir(parents=True)
    path.write_text("$btn-font-weight: $font-weight-normal !default;\n")


def test_bootstrap_default_variables_are_accepted(overlay, browser):
    write_bootstrap_variables(browser)
    (overlay / "theme" / "variables-it-before.scss").write_text(
        "$primary: #0066cc;\n$btn-font-weight: 600;\n"
    )
    apply(overlay, browser)
    assert "$btn-font-weight: 600;" in read(browser / "src/theme/variables.scss")


def test_bootstrap_variable_without_installed_bootstrap_fails(overlay, browser):
    (overlay / "theme" / "variables-it-before.scss").write_text("$btn-font-weight: 600;\n")
    with pytest.raises(OverlayError, match="btn-font-weight"):
        apply(overlay, browser)


def test_unknown_locale_key_fails(overlay, browser):
    (overlay / "locales" / "it" / "custom.json").write_text(
        json.dumps({"index": {"noSuchKey": "x"}})
    )
    with pytest.raises(OverlayError, match="index.noSuchKey"):
        apply(overlay, browser)


def test_cli_applies_the_given_overlay(overlay, browser):
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "apply_overlay.py"),
            str(browser),
            "--overlay",
            str(overlay),
        ],
        check=True,
    )
    assert '<html lang="it">' in read(browser / "index.html")


def test_fixture_widgets_config_is_the_empty_upstream_one():
    assert read(MINI / "widgets.config.js") == EMPTY_WIDGETS


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
