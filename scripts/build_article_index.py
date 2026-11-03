#!/usr/bin/env python3
"""Build the cross-project reading index without changing article URLs."""
import argparse
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://zipengwu.me"


def title(path):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
    match = re.search(r"^# (.+)$", text, re.M)
    if not match:
        raise ValueError(f"Missing article title: {path}")
    return re.sub(r"[*`]", "", match.group(1)).strip()


def build(sources):
    groups = []
    echo = [
        ("Time-series similarity: choosing between DTW, matrix profiles and learned representations", "/EchoTime/articles/time-series-similarity-guide.en.html", "English · Method selection"),
        ("时序相似性方法盘点：DTW、矩阵轮廓与学习表示该怎么选", "/EchoTime/articles/time-series-similarity-guide.zh-CN.html", "中文 · 方法选型"),
        ("What Does Similar Mean for a Time Series?", "/EchoTime/articles/what-time-series-similarity-measures.en.html", "English · Mechanisms, transformations and examples"),
        ("AI attention breakout analogs", "/EchoTime/blog/github_breakout_analogs.html", "Case study · Developer attention"),
        ("BTC vs VIX in 2024", "/EchoTime/blog/btc_vs_gold_under_shocks.html", "Case study · Market series"),
        ("Heatwave vs grid load", "/EchoTime/blog/heatwave_vs_grid_load.html", "Case study · Weather and energy"),
        ("Similarity lab", "/EchoTime/guide/similarity-lab.html", "Interactive method comparisons"),
    ]
    groups.append(("echotime", "EchoTime", "/EchoTime/", "Time-series similarity, method selection and worked examples.", [("Articles and examples", echo)]))

    detime = sources / "DeTime" / "docs"
    research = [(title(p), "/detime/docs/" + p.relative_to(detime).with_suffix("").as_posix() + "/", "Research guide") for p in sorted((detime / "research").glob("*.md")) if p.name not in {"index.md", "sharing-kit.md"}]
    tutorials = []
    for p in sorted((detime / "tutorials").rglob("*.md")):
        rel = p.relative_to(detime).with_suffix("").as_posix()
        if rel.endswith("/index"):
            rel = rel[:-5]
        else:
            rel += "/"
        tutorials.append((title(p), "/detime/docs/" + rel, "Tutorial series" if p.name == "index.md" else "Tutorial"))
    tutorials.insert(0, (title(detime / "ml-workflows.md"), "/detime/docs/ml-workflows/", "Features and forecasting workflows"))
    groups.append(("detime", "DeTime", "/detime/", "Decomposition research, Python workflows, quant research and the Hot Trend Lab.", [("Research articles", research), ("Tutorials and notebook walkthroughs", tutorials)]))

    tomc = sources / "TOMC" / "docs"
    guides = [
        ("Context Compression for LLM APIs with TOMC", "/tomc/guides/context-compression-api/", "Practical guide"),
        ("Reuse Project Notes Across Codex and Claude Code with TOMC", "/tomc/guides/shared-task-memory/", "Practical guide"),
        ("How to Measure Context Compression and AI Agent Memory", "/tomc/guides/measure-context-savings/", "Evaluation guide"),
    ]
    topics = ["context_ownership", "context_ownership_zh", "prompt_cache_20261017", "prompt_cache_20261017_zh", "comparison_with_llmlingua", "readers_and_agents", "readers_and_agents_zh", "codex_retention_20261005", "codex_retention_20261005_zh", "method", "paper_results", "model_context_limits_20261012"]
    technical = [(title(tomc / (name + ".md")), "/tomc/docs/" + name + "/", "中文" if name.endswith("_zh") else "Technical article") for name in topics]
    groups.append(("tomc", "TOMC Memory", "/tomc/", "Context compression, task memory, prompt caching and evaluation.", [("Practical guides", guides), ("Technical articles and research", technical)]))

    rows = [row for group in groups for _, items in group[4] for row in items]
    assert len({row[1] for row in rows}) == len(rows), "Duplicate article URLs"
    schema = {"@context": "https://schema.org", "@type": "CollectionPage", "url": BASE + "/articles/", "name": "Articles and Tutorials | Zipeng Wu", "author": {"@id": BASE + "/#person"}, "mainEntity": {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i, "name": name, "url": BASE + url} for i, (name, url, _) in enumerate(rows, 1)]}}
    sections = []
    for ident, name, url, description, categories in groups:
        content = []
        for heading, items in categories:
            lis = "\n".join(f'<li><a href="{escape(path)}">{escape(label)}</a><small>{escape(note)}</small></li>' for label, path, note in items)
            content.append(f'<h3>{heading}</h3><ul class="article-list">{lis}</ul>')
        sections.append(f'<section class="article-group" id="{ident}" aria-labelledby="{ident}-title"><h2 id="{ident}-title"><a href="{url}">{name}</a></h2><p class="article-intro">{description}</p>{"".join(content)}</section>')
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Articles and Tutorials: EchoTime, DeTime and TOMC Memory | Zipeng Wu</title>
<meta name="description" content="Read Zipeng Wu's articles and tutorials on time-series similarity, decomposition, quant research, context compression and AI task memory.">
<link rel="canonical" href="{BASE}/articles/"><link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/styles.css?v=20261010-tomc"><link rel="stylesheet" href="/projects.css">
<meta property="og:type" content="website"><meta property="og:title" content="Articles and Tutorials | Zipeng Wu"><meta property="og:url" content="{BASE}/articles/">
<meta property="og:description" content="Research articles and practical guides from EchoTime, DeTime and TOMC Memory."><meta name="twitter:card" content="summary">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script></head>
<body><a class="skip-link" href="#content">Skip to main content</a>
<header class="site-header"><div class="nav-inner"><a class="brand" href="/">Zipeng Wu</a><nav aria-label="Primary navigation"><a href="/research.html">Research</a><a href="/software.html">Projects</a><a class="active" aria-current="page" href="/articles/">Articles</a><a href="/publications.html">Publications</a></nav></div></header>
<main id="content" class="page"><nav class="project-nav" aria-label="Research projects"><a href="/EchoTime/">EchoTime</a><a href="/detime/">DeTime</a><a href="/tomc/">TOMC Memory</a></nav>
<h1>Articles and tutorials</h1><p>Research explanations, method comparisons and worked examples by Zipeng Wu, across three open-source projects.</p>
<nav class="article-jump" aria-label="Article collections"><a href="#echotime">Time-series similarity</a><a href="#detime">Decomposition and workflows</a><a href="#tomc">AI context and memory</a></nav>
{"".join(sections)}
<p>Looking for installation or API details? Visit <a href="/EchoTime/guide/">EchoTime documentation</a>, <a href="/detime/docs/">DeTime documentation</a> or <a href="/tomc/docs/">TOMC Memory documentation</a>.</p>
</main><footer class="site-footer"><div class="footer-inner">By <a href="/">Zipeng Wu</a> · <a href="/software.html">Research software</a></div></footer></body></html>'''
    destination = ROOT / "articles" / "index.html"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(html, encoding="utf-8")
    print(f"Built {destination.relative_to(ROOT)} with {len(rows)} article and tutorial links")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True, help="Directory containing TOMC and DeTime source checkouts")
    build(parser.parse_args().sources)
