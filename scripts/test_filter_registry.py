# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest",
#     "pyyaml",
# ]
# ///
"""Tests for filter_registry.py.

Usage:
    uv run scripts/test_filter_registry.py
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from filter_registry import filter_export, is_italian

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "registry-2026-11-24.json"
ITALIAN_IDS = {
    "anncsu",
    "bologna-open-data",
    "italian-cadastre",
    "lombardia-geoportale",
    "south-tyrol-geodata-portolan-mirror",
}


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def child_ids(export: dict) -> set[str]:
    return {
        link["portolan_registry:id"]
        for link in export["links"]
        if link["rel"] == "child"
    }


def entry(cid: str, *urls: str) -> dict:
    return {
        "rel": "child",
        "href": f"https://example.org/{cid}/catalog.json",
        "portolan_registry:id": cid,
        "portolan_registry:producers": [
            {"name": f"producer {i}", "url": url} for i, url in enumerate(urls)
        ],
    }


def test_selects_the_five_italian_catalogs():
    assert child_ids(filter_export(load_fixture(), set(), set())) == ITALIAN_IDS


def test_a_single_foreign_producer_excludes():
    ids = child_ids(filter_export(load_fixture(), set(), set()))
    assert "global-data" not in ids
    assert "harmonized-field-data" not in ids


def test_include_and_exclude_win():
    ids = child_ids(
        filter_export(
            load_fixture(), {"global-data"}, {"south-tyrol-geodata-portolan-mirror"}
        )
    )
    assert ids == (ITALIAN_IDS - {"south-tyrol-geodata-portolan-mirror"}) | {
        "global-data"
    }


def test_entry_without_producers_is_excluded_unless_included():
    empty = entry("empty")
    export = {"links": [empty]}
    assert child_ids(filter_export(export, set(), set())) == set()
    assert child_ids(filter_export(export, {"empty"}, set())) == {"empty"}


def test_host_check_handles_case_port_and_subdomains():
    assert is_italian(entry("a", "https://OPENDATA.Comune.Bologna.IT:443/x"))
    assert is_italian(entry("b", "https://www.agenziaentrate.gov.it/"))
    assert not is_italian(entry("c", "https://example.it.com/"))
    assert not is_italian(entry("d", "https://www.istat.it/", "https://example.org/"))
    assert is_italian(entry("e", "opendata.comune.bologna.it/no-scheme"))
    assert not is_italian(entry("f", "www.example.org/no-scheme"))


def test_non_child_links_and_other_fields_are_kept():
    export = load_fixture()
    out = filter_export(export, set(), set())
    assert [l for l in out["links"] if l["rel"] != "child"] == [
        l for l in export["links"] if l["rel"] != "child"
    ]
    for key in export:
        if key not in ("links", "count"):
            assert out[key] == export[key], key
    kept = [l for l in out["links"] if l["rel"] == "child"]
    original = {
        l["portolan_registry:id"]: l for l in export["links"] if l["rel"] == "child"
    }
    for link in kept:
        assert link == original[link["portolan_registry:id"]]


def test_count_matches_the_catalogs_kept():
    assert filter_export(load_fixture(), set(), set())["count"] == len(ITALIAN_IDS)


@pytest.mark.parametrize(
    "export",
    [
        {},
        {"links": "not a list"},
        {
            "links": [
                {
                    "rel": "child",
                    "portolan_registry:id": "x",
                    "portolan_registry:producers": "not a list",
                }
            ]
        },
        {"links": [{"rel": "child", "portolan_registry:producers": []}]},
    ],
    ids=["no-links", "links-not-list", "producers-not-list", "no-id"],
)
def test_malformed_export_fails(export):
    with pytest.raises(ValueError):
        filter_export(export, set(), set())


@pytest.mark.parametrize(
    "export",
    [
        # The registry's export schema requires producers on every child link,
        # so a missing key means the shape changed, not "no producers".
        {"links": [{"rel": "child", "portolan_registry:id": "x"}]},
        {"links": ["not a link"]},
        {"links": [{"rel": "child", "portolan_registry:id": "x",
                    "portolan_registry:producers": ["not a producer"]}]},
    ],
    ids=["producers-key-missing", "link-not-object", "producer-not-object"],
)
def test_changed_shape_fails(export):
    with pytest.raises(ValueError):
        filter_export(export, set(), set())


def test_cli_fails_when_no_catalog_is_left(tmp_path):
    # A renamed field would otherwise publish an empty start page.
    export = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for link in export["links"]:
        if link["rel"] == "child":
            for producer in link.get("portolan_registry:producers") or []:
                producer["href"] = producer.pop("url", "")
    source = tmp_path / "export.json"
    source.write_text(json.dumps(export), encoding="utf-8")
    overrides = tmp_path / "overrides.yaml"
    overrides.write_text("include: []\nexclude: []\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "filter_registry.py"),
         str(source), str(overrides), str(tmp_path / "out.json")],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "no catalog" in result.stderr.lower()
    assert not (tmp_path / "out.json").exists()


def test_cli_writes_the_filtered_export(tmp_path):
    overrides = tmp_path / "overrides.yaml"
    overrides.write_text("include: []\nexclude: [anncsu]\n", encoding="utf-8")
    out = tmp_path / "registry-it.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "filter_registry.py"),
            str(FIXTURE),
            str(overrides),
            str(out),
        ],
        check=True,
    )
    assert child_ids(json.loads(out.read_text(encoding="utf-8"))) == ITALIAN_IDS - {
        "anncsu"
    }


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
