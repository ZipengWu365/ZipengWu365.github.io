#!/usr/bin/env python3
"""Probe public source revisions and prepare a validated GitHub Pages artifact."""
import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://zipengwu.me"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
REPOSITORIES = {"tomc": "ZipengWu365/TOMC", "detime": "systems-mechanobiology/DeTime", "echotime": "ZipengWu365/EchoTime"}
ET.register_namespace("", NS)


def download(url, missing_ok=False):
    request = Request(url, headers={"User-Agent": "zipengwu-publication", "Cache-Control": "no-cache"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except HTTPError as error:
        if missing_ok and error.code == 404:
            return None
        raise


def source_revision(repository):
    data = subprocess.check_output(["git", "ls-remote", f"https://github.com/{repository}.git", "HEAD"], text=True)
    revision = data.split()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError(f"Invalid revision for {repository}")
    return revision


def sitemap_urls(url, visited=None):
    visited = set() if visited is None else visited
    if url in visited or urlsplit(url).netloc != "zipengwu.me":
        raise ValueError(f"Invalid/circular sitemap: {url}")
    visited.add(url)
    node = ET.fromstring(download(url))
    if node.tag == f"{{{NS}}}sitemapindex":
        result = set()
        for item in node.findall(f"{{{NS}}}sitemap/{{{NS}}}loc"):
            result.update(sitemap_urls(item.text, visited))
        return result
    if node.tag != f"{{{NS}}}urlset":
        raise ValueError("Unexpected sitemap format")
    return {item.text for item in node.findall(f"{{{NS}}}url/{{{NS}}}loc")}


def fingerprint(website_revision, revisions):
    return hashlib.sha256(json.dumps({"website_revision": website_revision, "source_revisions": revisions}, sort_keys=True).encode()).hexdigest()


def sitemap_dates(node):
    return {row.findtext(f"{{{NS}}}loc"): row.findtext(f"{{{NS}}}lastmod") for row in node if row.findtext(f"{{{NS}}}lastmod")}


def probe(output, github_output=None, force=False):
    revision = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    revisions = {key: source_revision(repository) for key, repository in REPOSITORIES.items()}
    raw = download(BASE + "/publication-state.json", missing_ok=True)
    previous = json.loads(raw) if raw is not None else None
    if previous is not None and (previous.get("schema_version") != 1 or not isinstance(previous.get("canonical_urls"), list)):
        raise ValueError("The published state has an unsupported format")
    key = fingerprint(revision, revisions)
    changed = force or previous is None or previous.get("fingerprint") != key
    # Bootstrap the URL contract from the currently published maps once. A fetch
    # error aborts rather than treating a temporary outage as deleted content.
    previous_urls = previous["canonical_urls"] if previous is not None else sorted(sitemap_urls(BASE + "/sitemap.xml"))
    previous_dates = (previous or {}).get("pages_lastmod")
    if changed and previous_dates is None:
        previous_dates = sitemap_dates(ET.fromstring(download(BASE + "/pages-sitemap.xml")))
    data = {"schema_version": 1, "website_revision": revision, "source_revisions": revisions,
            "fingerprint": key, "changed": changed, "previous_urls": previous_urls,
            "previous_article_index_sha256": (previous or {}).get("article_index_sha256"),
            "previous_pages_lastmod": previous_dates or {}}
    output.write_text(json.dumps(data, indent=2) + "\n")
    if github_output:
        with github_output.open("a") as stream:
            stream.write("changed=" + str(changed).lower() + "\n")
            for project, sha in revisions.items():
                stream.write(project + "_sha=" + sha + "\n")
    print(json.dumps({"changed": changed, "source_revisions": revisions}, indent=2))
    return data


def wait_for_echo(revision, destination, timeout=480):
    deadline = time.monotonic() + timeout
    while True:
        try:
            raw = download(BASE + "/EchoTime/publication-source.json", missing_ok=True)
            marker = json.loads(raw) if raw else {}
            if marker.get("source_revision") == revision:
                catalog = download(BASE + "/EchoTime/articles/catalog.json")
                sitemap = download(BASE + "/EchoTime/sitemap.xml")
                data = json.loads(catalog)
                if not isinstance(data.get("articles"), list):
                    raise ValueError("EchoTime catalog is missing its articles")
                if (hashlib.sha256(catalog).hexdigest() == marker.get("catalog_sha256") and
                        hashlib.sha256(sitemap).hexdigest() == marker.get("sitemap_sha256")):
                    node = ET.fromstring(sitemap)
                    if node.tag != f"{{{NS}}}urlset":
                        raise ValueError("Expected EchoTime's canonical URL set")
                    urls = {row.text for row in node.findall(f"{{{NS}}}url/{{{NS}}}loc")}
                    if any(not url.startswith(BASE + "/EchoTime/") for url in urls):
                        raise ValueError("EchoTime's map contains an unexpected host/path")
                    destination.write_bytes(catalog)
                    print("EchoTime publication is ready at the captured source revision and matching file hashes")
                    return urls
        except (HTTPError, URLError, TimeoutError) as error:
            if isinstance(error, HTTPError) and error.code not in {404, 408, 429} and error.code < 500:
                raise
        if time.monotonic() >= deadline:
            raise RuntimeError("EchoTime has not published the captured revision; retaining the live site and retrying at the next scheduled run")
        time.sleep(min(15, max(0, deadline - time.monotonic())))


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = None
        self.noindex = False
        self.refresh = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")
        if tag == "meta":
            self.noindex |= attrs.get("name") == "robots" and "noindex" in attrs.get("content", "")
            self.refresh |= attrs.get("http-equiv", "").lower() == "refresh"
        if tag in ("a", "link", "img", "script"):
            value = attrs.get("href") if tag in ("a", "link") else attrs.get("src")
            if value:
                self.links.append(value)


def page(path):
    result = Page()
    result.feed(path.read_text(encoding="utf-8"))
    return result


def write_xml(path, node):
    ET.indent(node, space="  ")
    ET.ElementTree(node).write(path, encoding="UTF-8", xml_declaration=True)


def build_sitemaps(article_index_changed, echo_urls, previous_dates=None):
    old = ET.parse(ROOT / "pages-sitemap.xml").getroot()
    dates = sitemap_dates(old)
    for url, date in (previous_dates or {}).items():
        # A later publication's real change date must survive the next clean
        # checkout; rebuilding unchanged text does not make it newly modified.
        dates[url] = max(dates.get(url) or "", date)
    urls = set()
    for path in ROOT.rglob("*.html"):
        relative = path.relative_to(ROOT)
        if relative.parts[0].startswith((".", "_")) or relative.parts[0] in {"scripts", "tests"}:
            continue
        if relative.parts[:2] in {("tomc", "docs"), ("detime", "docs")}:
            continue
        parsed = page(path)
        if parsed.canonical and parsed.canonical.startswith(BASE + "/") and not parsed.noindex and not parsed.refresh:
            urls.add(parsed.canonical)
    node = ET.Element(f"{{{NS}}}urlset")
    for url in sorted(urls):
        row = ET.SubElement(node, f"{{{NS}}}url")
        ET.SubElement(row, f"{{{NS}}}loc").text = url
        date = dates.get(url)
        if url == BASE + "/articles/" and article_index_changed:
            date = datetime.now(timezone.utc).date().isoformat()
        if date:
            ET.SubElement(row, f"{{{NS}}}lastmod").text = date
    write_xml(ROOT / "pages-sitemap.xml", node)
    index = ET.Element(f"{{{NS}}}sitemapindex")
    for path in ("/pages-sitemap.xml", "/EchoTime/sitemap.xml", "/detime/docs/sitemap.xml", "/tomc/docs/sitemap.xml"):
        row = ET.SubElement(index, f"{{{NS}}}sitemap")
        ET.SubElement(row, f"{{{NS}}}loc").text = BASE + path
    write_xml(ROOT / "sitemap.xml", index)
    for project in ("tomc", "detime"):
        urls.update(row.text for row in ET.parse(ROOT / project / "docs/sitemap.xml").findall(f"{{{NS}}}url/{{{NS}}}loc"))
    urls.update(echo_urls)
    return urls


def local_file(url):
    parts = urlsplit(url)
    if parts.netloc != "zipengwu.me" or not parts.path.startswith("/"):
        raise ValueError(f"Unexpected public URL: {url}")
    relative = unquote(parts.path).lstrip("/")
    if ".." in Path(relative).parts:
        raise ValueError("URL escapes publication directory")
    target = ROOT / relative
    return target / "index.html" if parts.path.endswith("/") or target.is_dir() else target


def preserve_urls(previous, canonical, redirects):
    missing = set(previous) - set(canonical)
    errors = [old for old in sorted(missing) if urlsplit(old).path not in redirects]
    # Recreate every configured alias on every clean build, including after the
    # old URL has ceased to be a canonical entry in the last published state.
    for old_path, target in redirects.items():
        if not old_path.startswith("/") or old_path.startswith("//") or urlsplit(old_path).query or urlsplit(old_path).fragment:
            raise ValueError(f"Invalid redirect source: {old_path}")
        old = BASE + old_path
        new = urljoin(BASE, target)
        if not target.startswith("/") or target.startswith("//") or new not in canonical:
            raise ValueError(f"Redirect target must be a published canonical page: {old} -> {target}")
        if urlsplit(old).path.startswith("/EchoTime/"):
            raise ValueError("EchoTime redirects must be implemented in the EchoTime project export")
        path = local_file(old)
        if path.exists():
            raise ValueError(f"Refusing to overwrite an existing page with a redirect: {old}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Page moved | Zipeng Wu</title>'
                        f'<link rel="canonical" href="{escape(new, quote=True)}"><meta http-equiv="refresh" content="0; url={escape(new, quote=True)}">'
                        f'</head><body><p>This page has moved to <a href="{escape(new, quote=True)}">its new address</a>.</p></body></html>')
    if errors:
        raise ValueError("Previously published URLs would disappear; add an intentional redirect before publishing:\n" + "\n".join(errors))


def validate_site(canonical, root=ROOT):
    errors = []
    echo_urls = {url for url in canonical if urlsplit(url).path.startswith("/EchoTime/")}
    for url in canonical - echo_urls:
        if not (root / local_file(url).relative_to(ROOT)).is_file():
            errors.append(f"Sitemap canonical has no published file: {url}")
    for path in root.rglob("*.html"):
        rel = path.relative_to(root)
        if rel.parts[0].startswith((".", "_")) or rel.parts[0] in {"scripts", "tests"}:
            continue
        parsed = page(path)
        if parsed.canonical and not parsed.noindex and not parsed.refresh and parsed.canonical not in canonical:
            errors.append(f"Canonical absent from maps: {rel}: {parsed.canonical}")
        current = BASE + "/" + rel.as_posix()
        for value in parsed.links:
            url = urljoin(current, value)
            parts = urlsplit(url)
            if parts.netloc != "zipengwu.me":
                continue
            if parts.path.startswith("/EchoTime/"):
                if parts.path.endswith((".html", "/")) and url.split("#")[0].split("?")[0] not in echo_urls:
                    # index.html and directory URLs share one canonical address.
                    alternate = re.sub(r"index\.html$", "", url.split("#")[0].split("?")[0])
                    if alternate not in echo_urls and alternate + "/" not in echo_urls:
                        errors.append(f"EchoTime link absent from its map: {rel}: {value}")
            elif not (root / local_file(url).relative_to(ROOT)).is_file():
                errors.append(f"Missing local page/asset: {rel}: {value}")
    if errors:
        raise ValueError("\n".join(errors[:30]))


def stage(destination):
    if destination.resolve() == ROOT or ROOT in destination.resolve().parents:
        raise ValueError("Artifact output must be outside the source checkout")
    if destination.exists():
        raise ValueError("Artifact output must be a new directory")
    excluded = {".git", ".github", "scripts", "tests", "_sources", "requirements-docs.txt", "README.md", "publication-redirects.json"}
    shutil.copytree(ROOT, destination, ignore=lambda directory, names: [name for name in names if name in excluded] if Path(directory) == ROOT else [])


def build(sources, probe_path, destination, echo_timeout):
    data = json.loads(probe_path.read_text())
    for project, folder in (("tomc", "TOMC"), ("detime", "DeTime"), ("echotime", "EchoTime")):
        sha = subprocess.check_output(["git", "-C", str(sources / folder), "rev-parse", "HEAD"], text=True).strip()
        if sha != data["source_revisions"][project]:
            raise ValueError(f"Source changed after probe: {project}")
    with tempfile.TemporaryDirectory(prefix="zipengwu-catalog-") as scratch:
        catalog = Path(scratch) / "echo-catalog.json"
        echo_urls = wait_for_echo(data["source_revisions"]["echotime"], catalog, echo_timeout)
        subprocess.run([sys.executable, str(ROOT / "scripts/sync_project_docs.py"), "--tomc-source", str(sources / "TOMC"), "--detime-source", str(sources / "DeTime")], check=True)
        subprocess.run([sys.executable, str(ROOT / "scripts/build_article_index.py"), "--sources", str(sources), "--echo-catalog", str(catalog)], check=True)
    article_hash = hashlib.sha256((ROOT / "articles/index.html").read_bytes()).hexdigest()
    canonical = build_sitemaps(article_hash != data.get("previous_article_index_sha256"), echo_urls, data.get("previous_pages_lastmod"))
    redirects = json.loads((ROOT / "publication-redirects.json").read_text())
    preserve_urls(data["previous_urls"], canonical, redirects)
    validate_site(canonical)
    state = {"schema_version": 1, "website_revision": data["website_revision"], "source_revisions": data["source_revisions"],
             "fingerprint": data["fingerprint"], "canonical_urls": sorted(canonical), "article_index_sha256": article_hash,
             "pages_lastmod": sitemap_dates(ET.parse(ROOT / "pages-sitemap.xml").getroot())}
    (ROOT / "publication-state.json").write_text(json.dumps(state, indent=2) + "\n")
    stage(destination)
    validate_site(canonical, destination)
    print(json.dumps({"artifact": str(destination), "canonical_urls": len(canonical), "source_revisions": state["source_revisions"]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("probe")
    check.add_argument("--output", type=Path, required=True)
    check.add_argument("--github-output", type=Path)
    check.add_argument("--force", action="store_true")
    publish = commands.add_parser("build")
    publish.add_argument("--sources", type=Path, required=True)
    publish.add_argument("--probe", type=Path, required=True)
    publish.add_argument("--output", type=Path, required=True)
    publish.add_argument("--echo-timeout", type=int, default=480)
    args = parser.parse_args()
    if args.command == "probe":
        probe(args.output, args.github_output, args.force)
    else:
        build(args.sources, args.probe, args.output, args.echo_timeout)


if __name__ == "__main__":
    main()
