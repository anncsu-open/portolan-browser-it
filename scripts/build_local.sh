#!/usr/bin/env bash
# Build the site locally the way CI does: check out the pinned browser
# release into .upstream/, filter the registry, apply the overlay, build.
# REGISTRY_EXPORT points at a registry export; the default is the saved
# fixture, so a local build needs no network beyond the clone and install.
set -euo pipefail
cd "$(dirname "$0")/.."

tag=$(tr -d '[:space:]' < browser.version)
rm -rf .upstream
git clone --quiet --depth 1 --branch "$tag" \
  https://github.com/portolan-sdi/portolan-browser.git .upstream

uv run scripts/filter_registry.py \
  "${REGISTRY_EXPORT:-tests/fixtures/registry-2026-11-24.json}" \
  overrides.yaml public/registry-it.json
# Install first: the applier checks our variables against Bootstrap's own.
(cd .upstream && npx -y pnpm@10 install --frozen-lockfile)
uv run scripts/apply_overlay.py .upstream

cd .upstream
SB_CONFIG=../config.it.js SB_pathPrefix=/portolan-browser-it/ npx -y pnpm@10 run build
echo "Built .upstream/dist from portolan-browser $tag"
