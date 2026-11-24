# Portolan Browser with the Italian public administration look

Status: design, 2026-11-24. Not implemented.

Name: **Portolan Browser Italia**. Repository `anncsu-open/portolan-browser-it`,
site `https://anncsu-open.github.io/portolan-browser-it/`. It starts in the
`anncsu-open` organisation and is then proposed to `portolan-sdi`, which hosts
`portolan-nl-demo` the same way (decided by Franc on 2026-11-24).

## Intent

Give Italian Portolan catalogs an extra way to be browsed: the official
Portolan Browser, unchanged in behaviour, dressed in the visual language of
the Italian public administration (Designers Italia / Bootstrap Italia, the
AgID guidelines). A catalog publisher adds this link next to the one for
`browser.portolan-sdi.org`.

It is a skin, not a product. It must not compete with Portolan Browser: no
features of its own, no divergent code, every release of the official browser
usable as soon as we choose to adopt it.

## Goals

- The official Portolan Browser, at a pinned release, built with an Italian
  PA theme and Italian as the default language.
- A start page that lists the Italian catalogs of the Portolan registry.
- Deep links `#/external/<catalog url>` that open any catalog in the skin, so
  a publisher can link it from its own README.
- A static site on GitHub Pages, rebuilt by CI.

## Non-goals

- New browser features, a different map, a curated portal with editorial
  pages (the DHIS2 Nepal geoservice is a portal of that kind; this is not).
- Fixing catalog-specific limits of the browser, such as the missing preview
  of `indirizzi-h3` behind an R2 `s3://` glob.
- A separate registry or any catalog list maintained by hand beyond the
  overrides file below.

## Anti-goals

- Anything that makes the site look like an official site of an
  administration, or that could be mistaken for one.
- A fork that drifts: once our repository holds browser source code beyond
  the overridden files, the approach has failed.

## Approach (chosen: 2)

1. Fork of `portolan-browser`, as `portolan-sdi/portolan-nl-demo` does.
   Rejected for now: every upstream release becomes a merge, with conflicts on
   exactly the files we change.
2. **Overlay on a pinned release, no fork.** Our repository holds only our
   files. CI checks out `portolan-sdi/portolan-browser` at a tag, copies the
   overlay over it, builds, and deploys. Upgrading means changing the tag.
   If an upstream release renames an overridden file, the build fails visibly.
   Chosen by Franc on 2026-11-24, "per ora".
3. A supported theming hook upstream, so a national skin is configuration
   only. Kept as a later contribution if the overlay grows beyond theme,
   configuration and `index.html`.

## What the overlay contains

| Path in our repo | What it does to the browser | Purpose |
|---|---|---|
| `browser.version` | — | The pinned tag, starting at `v0.2.0` |
| `config.it.js` | passed with `SB_CONFIG`, merged over the browser's `config.js` | Options below |
| `index.html` edits | anchored edits to `index.html` | Italian `lang`, self-hosted fonts, favicon |
| `widgets.config.js` | replaces the browser's, which is empty upstream | A footer line on who runs the site, one built-in `CustomText` widget per language |
| `theme/variables-it.scss` | appended to `src/theme/variables.scss` | Bootstrap variables mapped to the Designers Italia tokens |
| `theme/custom-it.scss` | appended to `src/theme/custom.scss` | Header, footer and component styling |
| `locales/{it,en}/custom.json` | deep-merged into `src/locales/{it,en}/custom.json` | Missing Italian strings and our own labels |
| `public/` | merged into `public/` | Logo, favicon, fonts, `registry-it.json` |
| `overrides.yaml` | — | Registry ids to add or exclude by hand |
| `scripts/` | — | The registry filter, the overlay applier, their tests |

Browser files are extended, never copied: an upstream release keeps its own
changes to them, and a moved anchor stops the build.

Nothing else of the browser is replaced. A component override, or any `.vue`
file in our repository, would be a sign to switch to approach 3.

### Header and footer

Static markup in `index.html` does not survive: `src/init.js` mounts the app on
`<body>`, and Vue empties the mount container first. The browser's supported
entry points are its widget slots `root-start`, `footer-start` and `root-end`
(`StacBrowser.vue`), configured in `widgets.config.js`. The overlay uses the
built-in `CustomText` widget in `footer-start` for the line on who runs the
site, once per language with a condition on the current locale. The centre
header and the footer are the browser's own. Our SCSS restyles them and
stretches them to the full page width, outside the `#stac-browser`
container; the footer links come from the configuration. No Vue source
enters our repository. Decided by the designer after the builder check;
fallback if the slots prove unusable: a script in `index.html` that inserts
the markup after mount.

### Translation

At `v0.2.0` the Italian `texts.json` lacks 47 of 418 keys, including every
registry string on the start page. The browser merges
`src/locales/<lang>/custom.json` over `texts.json`; the overlay carries
`custom.json` for `it` and `en` with the missing Italian strings, the footer
labels (`footerLinks.<label>`), and a reworded start-page line that says the
list is the Italian subset of the registry. The missing strings also go
upstream through the browser's translation workflow, so the overlay file
shrinks with later releases.

### Configuration

- `catalogUrl: null`, so the start page lists catalogs.
- `registryUrl`: our filtered copy, `registry-it.json`, served by the site.
- `allowExternalAccess: true`, so `#/external/<url>` opens any catalog.
- `locale: "it"`, `fallbackLocale: "en"`, `supportedLocales: ["it", "en"]`,
  `detectLocaleFromBrowser: false`.
- `historyMode: "hash"`, `pathPrefix` matching the Pages path.
- `catalogTitle: "Portolan Browser Italia"` and `catalogImage` with our logo.
- `footerLinks`: legal notes, privacy, the source repository, and a link to
  `browser.portolan-sdi.org` presented as the official browser.

### Look

- Tokens from Bootstrap Italia 2.x (BSD-3-Clause, 2.18.3 today): primary
  `#0066CC`, Titillium Web for text, Roboto Mono for code, its spacing and
  radii. They are mapped onto the browser's Bootstrap 5.3 variables. Bootstrap
  Italia's compiled CSS is not imported: two Bootstrap builds in one page
  would fight.
- Header following the Designers Italia "header center" pattern, with no
  slim bar (dropped by Franc on 2026-11-24). It has the bootstrap-italia
  measures: 120px high from the lg breakpoint, with a 28px name and an 82px
  logo; a 20px name and a 48px logo on small screens. It stays sticky. Once
  the page scrolls, it moves up and keeps 72px of the band on screen, with
  the browser's own name and logo sizes, much as the bootstrap-italia
  sticky header shrinks (decided by Franc on 2026-11-24). Below lg the band
  hides on scroll, as in the official browser. The footer names the hosting
  organisation (`anncsu-open` today, a single value to change when the
  project moves to `portolan-sdi`) and states that this is not an
  institutional site. The centre header
  carries "Portolan Browser Italia" and our logo, never the name or emblem of
  an administration.
- The logos the registry gives some catalogs (Comune di Bologna, Regione
  Lombardia, Provincia autonoma di Bolzano) stay on the start page: they
  identify who publishes each catalog, as on dati.gov.it, and the footer says
  the site is not institutional (decided by Franc on 2026-11-24).
- Footer following the Designers Italia footer pattern, with the footer links.
- Fonts self-hosted from the site; no Google Fonts or other third-party font
  requests. The other third-party requests of the browser stay and the
  privacy page lists them: CARTO basemaps (`basemaps.cartocdn.com`), the
  satellite style (`cholmes.github.io`), `epsg.io` for coordinate systems the
  browser does not know, the hosts of registry logos, the catalogs' own
  hosts, and GitHub Pages as the host of the site (decided by Franc on
  2026-11-24).
- Accessibility: the theme keeps WCAG 2.1 AA contrast; checked with an
  automated audit on the start page and on one catalog page.

### Which catalogs the start page lists

The registry export (`exports/catalogs.json` in `portolan-sdi/portolan-registry`)
is a STAC catalog whose child links are the registered catalogs, with
`portolan_registry:*` metadata. `bbox` cannot select Italy: Bologna declares
the whole globe and the South Tyrol mirror half of Europe. The producers'
URLs can: all five Italian catalogs of 2026-11-24 have at least one producer
whose host ends in `.it` (`anncsu`, `bologna-open-data`,
`lombardia-geoportale`, `italian-cadastre`,
`south-tyrol-geodata-portolan-mirror`).

Rule: a catalog is listed when every producer URL has a host ending in `.it`,
plus the ids in `overrides.yaml` under `include`, minus those under
`exclude`. "At least one producer" was rejected: it also selects
`global-data` and `harmonized-field-data` (Fields of the World), which list
the Provincia di Bolzano among about 90 producers, and every future
multinational catalog with one Italian contributor would need an exclusion by
hand. An Italian catalog with a foreign producer goes under `include`. The
output keeps the export's structure and fields, only fewer child links, so the
browser reads it unchanged. A test pins the five ids of today against a saved
copy of the export.

The filter runs in CI at every build. A scheduled build runs daily, after the
registry's nightly crawl, so the list follows the registry without a manual
step.

## CI

- On push to `main`, on a daily schedule, and by hand.
- Steps: read `browser.version`; check out the browser at that tag; run the
  filter tests and write `public/registry-it.json`; copy the overlay; install
  with the browser's lockfile; build with the browser's own build command;
  deploy `dist/` to GitHub Pages.
- A failed filter or build deploys nothing; the previous site stays up.

## Adoption

The first catalog to link it is ANNCSU: `anncsu-viewer` adds the deep link to
its catalog README and AGENTS files next to the existing Portolan Browser
link, once the site is live. That change belongs to `anncsu-viewer`, not to
this repository.

## Left to the builder

The exact SCSS mapping, the header and footer markup within the Designers
Italia patterns, the font files, the filter's language (Python with `uv`, as
in the other Geobeyond repositories, unless the browser's toolchain makes Node
simpler), and the texts of the footer pages.
