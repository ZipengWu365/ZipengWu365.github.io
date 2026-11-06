# Zipeng Wu personal homepage

This repository hosts the root GitHub Pages site for Zipeng Wu:

https://zipengwu.me/

The original GitHub Pages address, https://zipengwu365.github.io/, redirects to this custom domain.

The site uses a lightweight multi-page academic profile structure. It presents:

- about/profile information;
- current research focuses in temporal/time-series representation for foundation and world models;
- news and selected updates;
- UKRI/AIRR Isambard-AI compute-only awards;
- University of Birmingham College PhD scholarship;
- selected ranked publications and presentations;
- selected research software: De-Time, EchoTime, and TOMC;
- an October 2026 TOMC project page at `/tomc/`, connected to sequence compression and symbolic representation within the temporal representation research theme;
- one current CV: `Zipeng_Wu_CV_Main_Compact_2026-11-06_v7.pdf`;
- ICML electronic contact pages: `/connect/` for an in-person LinkedIn QR and `/icml/` for research links and NFC cards.

The site is intentionally static: `index.html`, topic pages such as `publications.html` and `awards.html`, `styles.css`, and files under `assets/`.

## Search indexing

- Use `https://zipengwu.me/` for canonical URLs and internal homepage links.
- `robots.txt` permits crawling and advertises `https://zipengwu.me/sitemap.xml`.
- `/sitemap.xml` is the sitemap index for `/pages-sitemap.xml`, EchoTime, DeTime docs and TOMC docs. Keep page dates aligned with actual changes; exclude 404 pages, noindex contact pages and verification files. `/tomc/` is a substantive project homepage with its own canonical URL.
- Preserve both the existing Google verification meta tag and `googleaf7776f98ec037d2.html`; they are ownership verification methods, not ranking signals.
- Search Console uses the URL-prefix property `https://zipengwu.me/`. Submit `sitemap.xml` there and use URL Inspection for important updated pages. Domain properties require separate DNS verification.

## Projects and articles

The public project entry points are `/EchoTime/`, `/detime/` and `/tomc/`.
`/articles/` links directly to research articles, technical guides and notebook
walkthroughs across all three projects. Existing EchoTime article URLs and TOMC
guide URLs are retained. Source repositories, Issues and Releases remain on GitHub.

EchoTime is deployed by its own project Pages workflow; do not copy a second
EchoTime export into this repository. The root sitemap index references its
existing `https://zipengwu.me/EchoTime/sitemap.xml`.

DeTime and TOMC public documentation is built from pinned source checkouts into
`/detime/docs/` and `/tomc/docs/`. The **Sync project content and deploy** Actions
workflow checks all three public repositories every five minutes and also runs
when this website's `main` branch changes. GitHub may delay scheduled runs, so
this is a polling interval rather than a five-minute publication guarantee.

The workflow compares public source revisions with the last successful
`publication-state.json` on the live site. An unchanged check skips the build
and deployment. Updated source revisions rebuild public docs, discover articles,
regenerate all site maps, validate links and deploy one Pages artifact. It uses
the standard repository token with a separate Pages deployment job; no new
personal token or cross-repository secret is needed. Pages must use **GitHub
Actions** as its publishing source, with the existing `zipengwu.me` domain.

EchoTime still publishes its own project route on each push to `main`. The root
publisher waits for EchoTime's matching revision and validates the catalog/map
hashes before including new article links. Failed builds retain the previous
live artifact and will be retried by a later scheduled run. **Run workflow** in
Actions requests an immediate full rebuild.

To add content:

- EchoTime: add a public `docs/articles/<filename>.md`, including an H1 and an
  optional description/language header. The existing project workflow publishes
  `/EchoTime/articles/<filename>.html` and updates its catalog and sitemap.
- DeTime: add public Markdown under `docs/research/`, `docs/articles/`,
  `docs/guides/` or `docs/tutorials/`; research/tutorial articles are discovered
  by the global index. Existing documentation navigation follows `mkdocs.yml`.
- TOMC: add public Markdown under `docs/`; the global index discovers pages that
  are included in the public docs build. Existing `exclude_docs` rules continue
  to apply.

The source repositories retain code, Issues, Releases, draft/design exclusions
and version history. The build does not execute notebook or benchmark
generators. Generated documentation in this branch is a bootstrap snapshot;
the live artifact and `publication-state.json` record the automatically built
source revisions.

Previously published canonical URLs are checked against the last successful
publication. A missing URL stops deployment. Keep filenames stable; for an
intentional move, add an old-path-to-new-path entry to
`publication-redirects.json`. Static aliases are recreated on every publication,
while the sitemap lists the new canonical address. EchoTime aliases belong in
its own exporter because that route is deployed separately.

For a local docs-only refresh, install `requirements-docs.txt` in a virtual
environment and run `scripts/sync_project_docs.py --help` against source
checkouts. Then rebuild the article index:

```sh
python scripts/build_article_index.py --sources /path/to/project-checkouts --echo-catalog /path/to/echo-catalog.json
```

The checkouts directory must contain `DeTime/`, `TOMC/` and `EchoTime/`. Existing articles
stay at their current addresses; new docs URLs use the personal domain. The
former DeTime documentation site is retained during this first phase.
