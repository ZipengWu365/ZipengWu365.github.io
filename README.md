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
- one current CV: `Zipeng_Wu_Foundation_Model_Temporal_Representation_CV_20261018_174715UTC.pdf`;
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
`/detime/docs/` and `/tomc/docs/`. To refresh the published snapshot, install
`requirements-docs.txt` in a virtual environment and run the documented
`scripts/sync_project_docs.py --help` command against the updated source
checkouts. The build preserves the upstream public-documentation exclusions
and records source revisions; it does not run experiments or alter the source
repositories. Then rebuild the article index:

```sh
python scripts/build_article_index.py --sources /path/to/project-checkouts
```

The checkouts directory must contain `DeTime/` and `TOMC/`. Existing articles
stay at their current addresses; new docs URLs use the personal domain. The
former DeTime documentation site is retained during this first phase.
