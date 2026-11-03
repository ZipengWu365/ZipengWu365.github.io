import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch


def module(name, filename):
    path = Path(__file__).resolve().parents[1] / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


publication = module("publication", "publication.py")
catalog = module("article_index", "build_article_index.py")


class PublicationTests(unittest.TestCase):
    def test_a_later_real_article_change_date_survives_an_unchanged_rebuild(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "articles").mkdir()
            (root / "articles/index.html").write_text(f'<link rel="canonical" href="{publication.BASE}/articles/">')
            (root / "pages-sitemap.xml").write_text(f'<urlset xmlns="{publication.NS}"><url><loc>{publication.BASE}/articles/</loc><lastmod>2026-11-03</lastmod></url></urlset>')
            for name in ("tomc", "detime"):
                folder = root / name / "docs"
                folder.mkdir(parents=True)
                (folder / "sitemap.xml").write_text(f'<urlset xmlns="{publication.NS}"/>')
            with patch.object(publication, "ROOT", root):
                publication.build_sitemaps(False, set(), {publication.BASE + "/articles/": "2026-11-05"})
            self.assertEqual(publication.sitemap_dates(ET.parse(root / "pages-sitemap.xml").getroot())[publication.BASE + "/articles/"], "2026-11-05")

    def test_echo_catalog_and_map_must_match_the_marker_hashes(self):
        catalog_bytes = b'{"articles": []}'
        map_bytes = b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://zipengwu.me/EchoTime/</loc></url></urlset>'
        marker = {"source_revision": "f" * 40, "catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(), "sitemap_sha256": hashlib.sha256(map_bytes).hexdigest()}
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "catalog.json"
            with patch.object(publication, "download", side_effect=[json.dumps(marker).encode(), catalog_bytes, map_bytes]):
                self.assertEqual(publication.wait_for_echo("f" * 40, destination, 0), {publication.BASE + "/EchoTime/"})
            destination.unlink()
            with patch.object(publication, "download", side_effect=[json.dumps(marker).encode(), b'{"articles": [{"title": "raced"}]}', map_bytes]), self.assertRaises(RuntimeError):
                publication.wait_for_echo("f" * 40, destination, 0)
            self.assertFalse(destination.exists())

    def test_unchanged_source_revisions_skip_and_each_source_change_rebuilds(self):
        revisions = {name: str(number) * 40 for number, name in enumerate(publication.REPOSITORIES, 1)}
        website = "a" * 40
        previous = {"schema_version": 1, "canonical_urls": [], "pages_lastmod": {}, "fingerprint": publication.fingerprint(website, revisions)}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "probe.json"
            with patch.object(publication.subprocess, "check_output", return_value=website), patch.object(publication, "download", return_value=json.dumps(previous).encode()), patch.object(publication, "source_revision", side_effect=lambda repo: revisions[next(name for name, value in publication.REPOSITORIES.items() if value == repo)]):
                self.assertFalse(publication.probe(output)["changed"])
                for name in revisions:
                    original = revisions[name]
                    revisions[name] = "f" * 40
                    self.assertTrue(publication.probe(output)["changed"], name)
                    revisions[name] = original

    def test_missing_published_url_blocks_deployment(self):
        with self.assertRaisesRegex(ValueError, "would disappear"):
            publication.preserve_urls([publication.BASE + "/removed/"], set(), {})

    def test_redirect_is_recreated_on_every_clean_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            new = publication.BASE + "/new/"
            old = publication.BASE + "/old/"
            redirects = {"/old/": "/new/"}
            with patch.object(publication, "ROOT", root):
                publication.preserve_urls([old], {new}, redirects)
                self.assertIn(new, (root / "old/index.html").read_text())
                (root / "old/index.html").unlink()
                publication.preserve_urls([new], {new}, redirects)
                self.assertTrue((root / "old/index.html").is_file())

    def test_canonical_typo_cannot_publish_a_404(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            typo = publication.BASE + "/typo/"
            (root / "index.html").write_text(f'<link rel="canonical" href="{typo}">')
            with patch.object(publication, "ROOT", root), self.assertRaisesRegex(ValueError, "has no published file"):
                publication.validate_site({typo}, root)

    def test_final_artifact_rejects_links_to_excluded_source_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            (root / "scripts").mkdir()
            (root / "scripts/private.py").write_text("example")
            (root / "index.html").write_text(f'<link rel="canonical" href="{publication.BASE}/"><a href="/scripts/private.py">bad link</a>')
            staged = Path(directory) / "artifact"
            with patch.object(publication, "ROOT", root):
                publication.stage(staged)
                with self.assertRaisesRegex(ValueError, "Missing local"):
                    publication.validate_site({publication.BASE + "/"}, staged)

    def test_directory_links_resolve_with_or_without_trailing_slash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            with patch.object(publication, "ROOT", root):
                self.assertEqual(publication.local_file(publication.BASE + "/docs"), root / "docs/index.html")
                self.assertEqual(publication.local_file(publication.BASE + "/docs/"), root / "docs/index.html")

    def test_new_tomc_and_detime_articles_appear_without_editing_the_index_script(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "site"
            root.mkdir()
            sources = Path(directory) / "sources"
            tomc = sources / "TOMC/docs"
            detime = sources / "DeTime/docs"
            tomc.mkdir(parents=True)
            (detime / "research").mkdir(parents=True)
            (tomc / "new-essay.md").write_text("# A new TOMC essay\n\nPublic article.")
            (detime / "research/new-guide.md").write_text("# A new DeTime guide\n")
            (detime / "ml-workflows.md").write_text("# ML workflows\n")
            manifest = {"tomc": {"html_pages": ["new-essay/index.html"]}, "detime": {"html_pages": ["research/new-guide/index.html", "ml-workflows/index.html"]}}
            (root / "project-docs-sources.json").write_text(json.dumps(manifest))
            echo = Path(directory) / "echo.json"
            echo.write_text(json.dumps({"articles": [{"title": "New Echo article", "path": "articles/new.en.html", "language": "en"}]}))
            with patch.object(catalog, "ROOT", root):
                catalog.build(sources, echo)
            rendered = (root / "articles/index.html").read_text()
            for path in ["/tomc/docs/new-essay/", "/detime/docs/research/new-guide/", "/EchoTime/articles/new.en.html"]:
                self.assertIn(path, rendered)


if __name__ == "__main__":
    unittest.main()
