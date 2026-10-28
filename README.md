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
- Keep sitemap dates aligned with actual page changes. Add new canonical content pages, but exclude the 404 page, the noindex contact QR page, verification files, and the `/tomc/` redirect.
- Preserve both the existing Google verification meta tag and `googleaf7776f98ec037d2.html`; they are ownership verification methods, not ranking signals.
- Search Console uses the URL-prefix property `https://zipengwu.me/`. Submit `sitemap.xml` there and use URL Inspection for important updated pages. Domain properties require separate DNS verification.
