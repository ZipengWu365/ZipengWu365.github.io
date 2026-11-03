#!/usr/bin/env python3
"""Build public project documentation at stable zipengwu.me URLs.

Install requirements-docs.txt, then pass local, clean Git source checkouts.
This builds checked-in documentation and assets only; it never runs the project
packages, notebook generators, benchmarks, or deployment commands.
"""

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://zipengwu.me"
PROJECTS = {
    "tomc": {"repository": "ZipengWu365/TOMC", "name": "TOMC Memory", "old_url": None},
    "detime": {"repository": "systems-mechanobiology/DeTime", "name": "DeTime",
               "old_url": "https://systems-mechanobiology.github.io/DeTime/"},
}
NETWORK_NAV = '''
<nav class="domain-project-nav" aria-label="Research projects and articles">
  <a href="/">Zipeng Wu</a><a href="/software.html">Projects</a>
  <a href="/articles/">Articles</a><a href="/EchoTime/">EchoTime</a>
  <a href="/detime/">DeTime</a><a href="/tomc/">TOMC Memory</a>
</nav>
<style>
.domain-project-nav{display:flex;flex-wrap:wrap;gap:.55rem 1.25rem;
max-width:1320px;margin:0 auto 1rem;padding:.8rem 1rem;
border-bottom:1px solid #d7dfe6;font-size:.9rem;line-height:1.5}
.domain-project-nav a{color:#0f6680;text-decoration:none}
.domain-project-nav a:hover,.domain-project-nav a:focus-visible{text-decoration:underline}
.domain-project-nav a:focus-visible{outline:2px solid #c98a00;outline-offset:3px}
/* Accommodate Bootstrap 5 utility navigation and the upstream DeTime theme. */
.navbar.fixed-top>.container{min-width:0;max-width:100%}
.navbar.fixed-top #navbar-collapse{min-width:0;max-width:100%;flex-wrap:wrap}
.navbar.fixed-top #navbar-collapse>.navbar-nav:first-child{
min-width:0;max-width:100%;flex-wrap:wrap}
.navbar.fixed-top #navbar-collapse>.navbar-nav.ms-md-auto{
display:flex!important;min-width:0;max-width:100%;flex:0 1 auto;flex-wrap:wrap}
@media(min-width:992px){
 .navbar.fixed-top #navbar-collapse>.navbar-nav:first-child{flex:1 1 auto}
 .navbar.fixed-top #navbar-collapse>.navbar-nav>li{min-height:44px}
 .navbar.fixed-top #navbar-collapse>.navbar-nav>li>.nav-link{
 min-height:44px;padding:.55rem .65rem}
 .navbar.fixed-top #navbar-collapse>.navbar-nav.ms-md-auto{margin-left:auto!important}
}
@media(max-width:991.98px){
 .navbar.fixed-top #navbar-collapse{overflow-x:hidden}
 .navbar.fixed-top #navbar-collapse>.navbar-nav.ms-md-auto{
 margin-left:0!important;align-items:stretch}
 .navbar.fixed-top #navbar-collapse .dropdown-menu{
 min-width:0!important;max-width:100%!important;width:100%;
 grid-template-columns:minmax(0,1fr)!important;box-sizing:border-box}
 .navbar.fixed-top #navbar-collapse .dropdown-item{
 white-space:normal;overflow-wrap:anywhere}
}
</style>
'''


def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()


def repository_url(repository, revision, path, image=False):
    if image:
        return f"https://raw.githubusercontent.com/{repository}/{revision}/{path}"
    return f"https://github.com/{repository}/blob/{revision}/{path}"


def normalize(path):
    parts = []
    for part in PurePosixPath(path).parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


def rewrite_url(url, source_file, repository, revision, tracked, excluded=(), image=False):
    pieces = urlsplit(html.unescape(url))
    if pieces.scheme or pieces.netloc or not pieces.path or pieces.path.startswith("/"):
        return url
    resolved = normalize((PurePosixPath("docs") / source_file.parent / unquote(pieces.path)).as_posix())
    # MkDocs handles paths inside docs, including Markdown-to-HTML conversion.
    # Root README, examples, notebooks and release evidence remain on GitHub.
    if (not resolved.startswith("docs/") or resolved in excluded) and resolved in tracked:
        return repository_url(repository, revision, resolved, image) + (
            ("?" + pieces.query) if pieces.query else "") + (
            ("#" + pieces.fragment) if pieces.fragment else "")
    return url


def rewrite_markdown(text, relative, repository, revision, tracked, excluded):
    def rewrite_chunk(chunk):
        def markdown_link(match):
            return match[1] + rewrite_url(match[2], relative, repository, revision, tracked, excluded,
                                          image=match[1].startswith("!")) + match[3]
        chunk = re.sub(r'(!?\[[^\]\n]*\]\()([^\s\)]+)([^\)\n]*\))', markdown_link, chunk)
        def reference(match):
            return match[1] + rewrite_url(match[2], relative, repository, revision, tracked, excluded) + match[3]
        chunk = re.sub(r'(^\s*\[[^\]\n]+\]:\s*)(\S+)(.*$)', reference, chunk, flags=re.M)
        def attribute(match):
            attr, quote, value = match.groups()
            return attr + quote + rewrite_url(value, relative, repository, revision, tracked, excluded,
                                               image=attr.lower().startswith("src")) + quote
        return re.sub(r'((?:href|src)=)([\"\'])([^\"\']+)\2', attribute, chunk, flags=re.I)
    # Leave fenced examples intact, including literal Markdown and HTML examples.
    chunks = re.split(r'(^\s*```[^\n]*\n.*?^\s*```[^\n]*$|^\s*~~~[^\n]*\n.*?^\s*~~~[^\n]*$)',
                      text, flags=re.M | re.S)
    return "".join(chunk if index % 2 else rewrite_chunk(chunk) for index, chunk in enumerate(chunks))


def augment_page(path, project):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'(<body\b[^>]*>)', lambda match: match[1] + NETWORK_NAV, text, count=1)
    # The default MkDocs 404 is not an article or a canonical index target.
    if path.name == "404.html":
        if not re.search(r'name=[\"\']robots[\"\']', text):
            text = text.replace("</head>", '<meta name="robots" content="noindex, follow">\n</head>', 1)
    else:
        canonical = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', text)
        title = re.search(r'<title>(.*?)</title>', text, re.S)
        if canonical and title:
            url = html.unescape(canonical[1])
            title = html.unescape(re.sub(r"<[^>]+>", "", title[1]))
            relative = path.relative_to(ROOT / project / "docs").as_posix()
            language = "zh-CN" if "_zh/" in relative else "en"
            text = re.sub(r'<html lang="[^"]*"', '<html lang="' + language + '"', text, count=1)
            metadata = ""
            if not re.search(r'<meta\s+name="description"', text):
                description = title + ": " + PROJECTS[project]["name"] + " documentation and practical guides by Zipeng Wu."
                metadata += '<meta name="description" content="' + html.escape(description, quote=True) + '">\n'
            if project == "tomc" or relative.startswith(("research/", "tutorials/")):
                article = {"@context": "https://schema.org", "@type": "TechArticle",
                           "@id": url + "#article", "url": url, "headline": title,
                           "mainEntityOfPage": url, "inLanguage": language,
                           "author": {"@type": "Person", "@id": DOMAIN + "/#person",
                                      "name": "Zipeng Wu", "url": DOMAIN + "/"}}
                metadata += '<script type="application/ld+json">' + json.dumps(article).replace("</", "<\\/") + '</script>\n'
            text = text.replace("</head>", metadata + "</head>", 1)
    path.write_text(text, encoding="utf-8")


def build(project, source):
    details = PROJECTS[project]
    source = source.resolve()
    revision = git(source, "rev-parse", "HEAD")
    tracked = set(git(source, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    public_url = f"{DOMAIN}/{project}/docs/"
    output = ROOT / project / "docs"
    config = yaml.safe_load((source / "mkdocs.yml").read_text(encoding="utf-8"))
    if project == "tomc":
        # The upstream flat navigation has dozens of top-level links. Group the
        # same public documents so the domain publication also fits desktop.
        config["nav"] = [
            {"Overview": "index.md"},
            {"Install": [{"Assistant plugins": "assistant_plugin.md"},
                         {"Assistant plugins (中文)": "assistant_plugin_zh.md"},
                         {"Desktop companion": "desktop_companion.md"},
                         {"macOS": "macos_usage.md"}, {"Manual MCP setup": "assistant_setup.md"},
                         {"Cursor and TRAE": "cursor_trae.md"},
                         {"Cursor and TRAE (中文)": "cursor_trae_zh.md"},
                         {"WorkBuddy": "workbuddy.md"}, {"WorkBuddy (中文)": "workbuddy_zh.md"},
                         {"DeepSeek Harness": "deepseek_harness.md"},
                         {"DeepSeek Harness (中文)": "deepseek_harness_zh.md"}]},
            {"Guides": [{"Quickstart": "quickstart.md"}, {"Usage tips": "usage_tips.md"},
                        {"Usage tips (中文)": "usage_tips_zh.md"},
                        {"Context ownership": "context_ownership.md"},
                        {"Context ownership (中文)": "context_ownership_zh.md"},
                        {"Prompt caching": "prompt_cache_20261017.md"},
                        {"Prompt caching (中文)": "prompt_cache_20261017_zh.md"},
                        {"Model context limits": "model_context_limits_20261012.md"}]},
            {"Reference": [{"Python API": "api_reference.md"}, {"Method": "method.md"},
                           {"Architecture": "architecture.md"},
                           {"LLMLingua comparison": "comparison_with_llmlingua.md"}]},
            {"Research": [{"Paper scope": "paper_scope.md"},
                          {"Readers and agent hosts": "readers_and_agents.md"},
                          {"Readers and agent hosts (中文)": "readers_and_agents_zh.md"},
                          {"Paper results": "paper_results.md"},
                          {"Claims and limitations": "claims_and_limitations.md"},
                          {"Reproducibility": "reproducibility.md"},
                          {"Data and licensing": "data_and_license.md"}]},
            {"Validation": [{"Platform checks": "platform_checks.md"},
                            {"Platform checks (中文)": "platform_checks_zh.md"},
                            {"Windows installation": "windows_installation_feedback.md"},
                            {"Windows installation (中文)": "windows_installation_feedback_zh.md"},
                            {"Codex input comparison": "codex_retention_20261005.md"},
                            {"Codex input comparison (中文)": "codex_retention_20261005_zh.md"},
                            {"Linux installation": "linux_validation.md"},
                            {"DeepSeek Harness validation": "deepseek_harness_validation_20261029.md"},
                            {"Validation record": "validation.md"}]},
            {"Project": [{"Legacy compatibility": "legacy_extensions.md"},
                         {"Hugging Face Space": "huggingface_space.md"},
                         {"Repository traffic": "traffic_metrics.md"}]},
        ]
    if project == "detime":
        # Maintenance diaries and social-sharing instructions stay in GitHub.
        config["exclude_docs"] = config.get("exclude_docs", "") + "\n/maintenance/**\n/research/sharing-kit.md\n"
    import pathspec
    excluded_spec = pathspec.PathSpec.from_lines("gitwildmatch", config.get("exclude_docs", "").splitlines())
    excluded = {path for path in tracked if path.startswith("docs/") and excluded_spec.match_file(path[5:])}
    config.update({"site_url": public_url, "site_author": "Zipeng Wu",
                   "repo_url": f"https://github.com/{details['repository']}",
                   "repo_name": details["repository"], "edit_uri": "", "plugins": ["search"]})
    with tempfile.TemporaryDirectory(prefix=f"zipengwu-{project}-docs-") as scratch:
        scratch = Path(scratch)
        docs = scratch / "docs"
        shutil.copytree(source / "docs", docs)
        # Verification tokens belong to the original host property, not articles.
        for path in docs.glob("google*.html"):
            path.unlink()
        for path in docs.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            if details["old_url"]:
                text = text.replace(details["old_url"], public_url)
            text = rewrite_markdown(text, path.relative_to(docs), details["repository"], revision, tracked, excluded)
            if project == "tomc" and path.relative_to(docs).as_posix() == "index.md":
                text = text.replace(
                    "Direct `prepare_context` calls do not save history.",
                    "The current MCP runtime saves successful prepared contexts and their tasks locally by default. "
                    "Context recording can be disabled in the TOMC panel; existing snapshots remain until deleted.")
                text = text.replace(
                    "[TOMC Memory official GitHub home](https://github.com/ZipengWu365/TOMC)",
                    "[TOMC Memory project homepage](https://zipengwu.me/tomc/) · "
                    "[Source code on GitHub](https://github.com/ZipengWu365/TOMC)")
            path.write_text(text, encoding="utf-8")
        custom = source / config.get("theme", {}).get("custom_dir", "overrides")
        if custom.is_dir():
            overrides = scratch / "overrides"
            shutil.copytree(custom, overrides)
            for path in overrides.rglob("*"):
                if path.is_file():
                    text = path.read_text(encoding="utf-8")
                    if details["old_url"]:
                        text = text.replace(details["old_url"], public_url)
                    path.write_text(text, encoding="utf-8")
            config["theme"]["custom_dir"] = str(overrides)
        config["docs_dir"] = str(docs)
        config["site_dir"] = str(output)
        build_config = scratch / "mkdocs.yml"
        build_config.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
        subprocess.run([sys.executable, "-m", "mkdocs", "build", "--clean", "-f", str(build_config)], check=True)
    # Build timestamps are not evidence that every source article changed today.
    # Omit sitemap lastmod until accurate per-source change dates are available.
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    sitemap = output / "sitemap.xml"
    tree = ET.parse(sitemap)
    for url in tree.getroot():
        for date in list(url.findall(f"{{{namespace}}}lastmod")):
            url.remove(date)
    tree.write(sitemap, encoding="utf-8", xml_declaration=True)
    compressed = output / "sitemap.xml.gz"
    if compressed.exists():
        compressed.unlink()
    for path in output.rglob("*.html"):
        augment_page(path, project)
    license_text = git(source, "show", "HEAD:LICENSE")
    (output / "LICENSE.txt").write_text(license_text + "\n", encoding="utf-8")
    html_pages = sorted(path.relative_to(output).as_posix() for path in output.rglob("*.html") if path.name != "404.html")
    return {"repository": details["repository"], "revision": revision,
            "source_commit_date": git(source, "show", "-s", "--format=%cI", "HEAD"),
            "site_url": public_url, "html_pages": html_pages,
            "sitemap_url": public_url + "sitemap.xml",
            "source_config_sha256": hashlib.sha256((source / "mkdocs.yml").read_bytes()).hexdigest(),
            "output_bytes": sum(path.stat().st_size for path in output.rglob("*") if path.is_file())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tomc-source", type=Path)
    parser.add_argument("--detime-source", type=Path)
    args = parser.parse_args()
    manifests = {}
    for project in PROJECTS:
        source = getattr(args, project + "_source")
        if source:
            manifests[project] = build(project, source)
    if not manifests:
        parser.error("pass --tomc-source and/or --detime-source")
    manifest_path = ROOT / "project-docs-sources.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    previous.update(manifests)
    manifest_path.write_text(json.dumps(previous, indent=2) + "\n")
    print(json.dumps({key: {"html_pages": len(value["html_pages"]), "bytes": value["output_bytes"],
                            "revision": value["revision"]} for key, value in manifests.items()}, indent=2))


if __name__ == "__main__":
    main()
