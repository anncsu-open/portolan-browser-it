# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
# ]
# ///
"""Keep the Italian catalogs of a Portolan registry export.

Usage:
    uv run scripts/filter_registry.py <export.json> <overrides.yaml> <out.json>

The export is a STAC catalog whose child links are the registered catalogs.
A catalog is Italian when every producer URL has a host ending in ".it".
`bbox` cannot be used: some Italian catalogs declare the whole globe. The
ids under `include` in the overrides file are kept anyway, those under
`exclude` are dropped. Everything else in the export is kept as it is, so the
browser reads the output like the original; only `count` is set to the number
of catalogs kept.
"""

import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml


def _producers(entry: dict) -> list[dict]:
    """The producers of a child link, checked against the export's schema.

    The registry's export schema requires `portolan_registry:producers` on
    every child link, so a missing key or a value of another shape means the
    export changed, not that the catalog has no producers.
    """
    cid = entry.get("portolan_registry:id")
    if "portolan_registry:producers" not in entry:
        raise ValueError(f"{cid}: portolan_registry:producers is missing")
    producers = entry["portolan_registry:producers"]
    if not isinstance(producers, list) or not all(
        isinstance(producer, dict) for producer in producers
    ):
        raise ValueError(f"{cid}: portolan_registry:producers is not a list of objects")
    return producers


def _host(url: str) -> str:
    """The lowercased host of a URL, also when the scheme is missing."""
    return (urlsplit(url if "://" in url else f"//{url}").hostname or "").lower()


def is_italian(entry: dict) -> bool:
    """True when the catalog has producers and every one is on a .it host."""
    producers = _producers(entry)
    if not producers:
        return False
    for producer in producers:
        if not _host(str(producer.get("url", ""))).endswith(".it"):
            return False
    return True


def filter_export(export: dict, include: set[str], exclude: set[str]) -> dict:
    """The export with only the Italian child links, plus and minus overrides."""
    links = export.get("links")
    if not isinstance(links, list):
        raise ValueError("the registry export has no list of links")

    kept = []
    for link in links:
        if not isinstance(link, dict):
            raise ValueError(f"a link of the registry export is not an object: {link!r}")
        if link.get("rel") != "child":
            kept.append(link)
            continue
        cid = link.get("portolan_registry:id")
        if not cid:
            raise ValueError(
                f"a child link has no portolan_registry:id: {link.get('href')}"
            )
        if cid in exclude:
            continue
        if cid in include or is_italian(link):
            kept.append(link)

    out = dict(export)
    out["links"] = kept
    if "count" in export:
        out["count"] = sum(1 for link in kept if link.get("rel") == "child")
    return out


def load_overrides(path: Path) -> tuple[set[str], set[str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return set(data.get("include") or []), set(data.get("exclude") or [])


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    export_path, overrides_path, out_path = map(Path, argv)
    include, exclude = load_overrides(overrides_path)
    export = json.loads(export_path.read_text(encoding="utf-8"))
    out = filter_export(export, include, exclude)
    if not any(link.get("rel") == "child" for link in out["links"]):
        # Publishing would hide the list without any warning to visitors.
        print(
            "No catalog is left after filtering: the registry export may have "
            "changed shape. Nothing written.",
            file=sys.stderr,
        )
        return 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ids = sorted(
        l["portolan_registry:id"] for l in out["links"] if l.get("rel") == "child"
    )
    print(f"Kept {len(ids)} catalogs: {', '.join(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
