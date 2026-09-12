#!/usr/bin/env python3
"""Static site generator for The Headless Studio.

Usage: python3 build.py            # builds content/*.md -> site/
No framework, no config file. Front matter is a simple key: value block
between --- lines at the top of each markdown file. Articles are anything
with a `date:`; pages (about.md) have none. Output is plain HTML + one CSS
file + an RSS feed -- drop site/ on GitHub Pages, Netlify, or any host.
"""

import datetime
import email.utils
import html
import os
import re
import shutil

import markdown
from pygments.formatters import HtmlFormatter

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
STATIC = os.path.join(ROOT, "static")
SITE = os.path.join(ROOT, "site")
EBOOK = os.path.join(ROOT, "ebook-intermediate")  # the free book source

SITE_NAME = "The Headless Studio"
SITE_TAGLINE = "Music production as code. No DAW required."
BASE_PATH = "/headless-studio"  # subdirectory on the host; "" for a root deploy
SITE_URL = "https://clintjohnson.cloud" + BASE_PATH
AUTHOR = "Clint Johnson"

GITHUB_URL = "https://github.com/clintuitive/headless-studio"
COFFEE_URL = "https://buymeacoffee.com/clintjohnson"  # optional tip jar

MD_EXTENSIONS = ["fenced_code", "codehilite", "tables", "smarty", "attr_list"]
MD_CONFIG = {"codehilite": {"guess_lang": False, "css_class": "highlight"}}


def parse_front_matter(text):
    meta = {}
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        for line in fm.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"')
        return meta, body.strip()
    return meta, text


def reading_time(body):
    words = len(re.findall(r"\w+", body))
    return max(1, round(words / 220))


def rebase(page):
    """Prefix every root-absolute href/src with BASE_PATH so the site works
    from a subdirectory. Content and templates keep writing clean "/" paths."""
    if not BASE_PATH:
        return page
    return re.sub(r'(href|src|action)="/(?!/)', rf'\1="{BASE_PATH}/', page)


def page_shell(title, content, description=""):
    desc = html.escape(description or SITE_TAGLINE)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="/static/style.css?v=album-players-1">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="/feed.xml">
</head>
<body>
<header class="site-header">
  <a class="site-title" href="/">{SITE_NAME}<span class="cursor">_</span></a>
  <nav><a href="/">Articles</a><a href="/book.html">Book</a><a href="/music.html">Music</a><a href="https://clintjohnson.cloud/patchbay/" target="_blank" rel="noopener">The&nbsp;Patchbay&nbsp;&#8599;</a><a href="{GITHUB_URL}" target="_blank" rel="noopener">Code&nbsp;&#8599;</a><a href="/about.html">About</a></nav>
</header>
<main>
{content}
</main>
<footer class="site-footer">
  <p>&copy; {datetime.date.today().year} {AUTHOR} &middot; {SITE_TAGLINE}</p>
  <p class="footer-links"><a href="/book.html">Free book</a> &middot;
     <a href="{GITHUB_URL}">Code on GitHub (MIT)</a> &middot;
     <a href="/feed.xml">RSS</a> &middot;
     <a href="{COFFEE_URL}">Buy me a coffee</a></p>
</footer>
</body>
</html>"""


CTA = f"""
<aside class="cta">
  <h3>Get the next one in your inbox</h3>
  <p>I write about driving real studio tools — VST3 plugins, amp sims, samplers —
  entirely from Python. No fluff, always working code.</p>
  <p class="cta-small">Start with the self-contained examples.
  Older plugin rigs need their documented platform setup and assets.</p>
  <form action="https://buttondown.com/api/emails/embed-subscribe/headlessstudio"
        method="post" class="subscribe">
    <input type="email" name="email" placeholder="you@example.com" required>
    <button type="submit">Subscribe</button>
  </form>
  <p class="cta-small">The whole system is a <strong>free book</strong> — every script,
  every trick, a full album built in code, written for intermediate programmers
  (no audio background needed). <a href="/book.html">Read it free&nbsp;&rarr;</a></p>
  <p class="cta-small">And the complete working pipeline is
  <a href="{GITHUB_URL}">free and open on GitHub</a> (MIT). Take it, use it, make
  something.</p>
</aside>
"""


BOOK_FOOT = f"""
<aside class="book-foot">
  <p>This book is free, and so is <a href="{GITHUB_URL}">the code</a>. If it
  helped, you can <a href="{COFFEE_URL}">buy me a coffee</a> — always optional.</p>
  <form action="https://buttondown.com/api/emails/embed-subscribe/headlessstudio"
        method="post" class="subscribe">
    <input type="email" name="email" placeholder="you@example.com" required>
    <button type="submit">Get updates</button>
  </form>
</aside>
"""


def render_article(meta, body_html, minutes):
    date = datetime.date.fromisoformat(meta["date"])
    return f"""<article>
<header class="article-header">
  <h1>{html.escape(meta["title"])}</h1>
  <p class="meta"><time datetime="{meta["date"]}">{date.strftime("%B %-d, %Y")}</time>
     &middot; {minutes} min read &middot; {AUTHOR}</p>
</header>
{body_html}
</article>
{CTA}"""


def first_heading(md_text):
    """The book chapters/appendices start with a '# Title' line."""
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"


def build_book(site_dir):
    """Publish the full free book: a landing page, one page per chapter and
    appendix (with prev/next nav), and a single combined page for reading or
    printing to PDF. Reads ebook-intermediate/*.md."""
    if not os.path.isdir(EBOOK):
        print("  (no ebook-intermediate/ — skipping book)")
        return 0
    os.makedirs(os.path.join(site_dir, "book"), exist_ok=True)

    files = sorted(f for f in os.listdir(EBOOK)
                   if f.endswith(".md") and f != "README.md")
    # chapters first (chapter-01..15), then appendices (appendix-a..e)
    files.sort(key=lambda f: (not f.startswith("chapter"), f))

    parts = []
    for fname in files:
        with open(os.path.join(EBOOK, fname)) as fh:
            text = fh.read()
        md = markdown.Markdown(extensions=MD_EXTENSIONS, extension_configs=MD_CONFIG)
        parts.append({
            "slug": "book/" + os.path.splitext(fname)[0] + ".html",
            "title": first_heading(text),
            "html": md.convert(text),
            "is_appendix": fname.startswith("appendix"),
        })

    # Individual chapter pages with prev/next.
    for i, p in enumerate(parts):
        nav = '<nav class="book-nav">'
        nav += (f'<a href="/{parts[i-1]["slug"]}">&larr; Previous</a>'
                if i > 0 else '<span></span>')
        nav += '<a href="/book.html">Contents</a>'
        nav += (f'<a href="/{parts[i+1]["slug"]}">Next &rarr;</a>'
                if i < len(parts) - 1 else '<span></span>')
        nav += '</nav>'
        body = (f'<article class="book-chapter">{p["html"]}</article>'
                f'{nav}{BOOK_FOOT}')
        page = page_shell(f'{p["title"]} — {SITE_NAME}', body,
                          f'{p["title"]} — from the free book The Headless Studio.')
        with open(os.path.join(site_dir, p["slug"]), "w") as fh:
            fh.write(rebase(page))

    # Combined single-page edition (read straight through / print to PDF).
    combined = ['<article class="book-chapter book-full">']
    combined.append(f'<h1>The Headless Studio</h1><p class="meta">'
                    f'Making Records with Python — No DAW Required &middot; '
                    f'{AUTHOR}</p><hr>')
    for p in parts:
        combined.append(p["html"])
        combined.append('<hr>')
    combined.append('</article>')
    with open(os.path.join(site_dir, "book", "the-headless-studio.html"), "w") as fh:
        fh.write(rebase(page_shell("The Headless Studio — full book",
                                   "\n".join(combined),
                                   "The complete free book, on one page.")))

    # Book landing page.
    chap_items, appx_items = [], []
    for p in parts:
        li = f'<li><a href="/{p["slug"]}">{html.escape(p["title"])}</a></li>'
        (appx_items if p["is_appendix"] else chap_items).append(li)
    landing = f"""<section class="book-hero">
  <img class="book-cover-shot" src="/images/book-cover.jpg" width="210" height="315"
       alt="The Headless Studio — book cover">
  <h1>The Headless Studio</h1>
  <p class="book-sub">Making Records with Python — No DAW Required</p>
  <p>The whole system, free and complete: {len(chap_items)} chapters and
  {len(appx_items)} appendices, written for an intermediate programmer with no
  audio background. It walks the entire pipeline — hosting plugins headlessly,
  rescuing incompatible ones, mapping your own sample instruments, synthesis
  from scratch, arranging as data, mixing, and verifying float stems against
  the working mix. Updated September 2026 with the album rebuilds. The code is
  <a href="{GITHUB_URL}">free and open on GitHub</a>.</p>
  <p class="book-actions">
    <a class="btn" href="/book/the-headless-studio.html">Read online</a>
    <a class="btn btn-ghost" href="/downloads/the-headless-studio.epub" download>Download EPUB</a>
    <a class="btn btn-ghost" href="{GITHUB_URL}">Get the code &#8599;</a>
  </p>
  <p class="book-dl-note">Free EPUB for your e-reader, phone, or tablet — or
  read every chapter right here in the browser.</p>
</section>
<section class="book-toc">
  <h2>Chapters</h2>
  <ol class="book-list">{''.join(chap_items)}</ol>
  <h2>Appendices</h2>
  <ul class="book-list">{''.join(appx_items)}</ul>
</section>
{BOOK_FOOT}"""
    with open(os.path.join(site_dir, "book.html"), "w") as fh:
        fh.write(rebase(page_shell(f"The Headless Studio — free book",
                                   landing,
                                   "The complete free book on making records "
                                   "with Python, no DAW — all chapters online.")))
    return len(parts)


def main():
    shutil.rmtree(SITE, ignore_errors=True)
    os.makedirs(os.path.join(SITE, "static"), exist_ok=True)
    if os.path.isdir(STATIC):
        for f in os.listdir(STATIC):
            shutil.copy(os.path.join(STATIC, f), os.path.join(SITE, "static", f))
    images = os.path.join(ROOT, "images")
    if os.path.isdir(images):
        shutil.copytree(images, os.path.join(SITE, "images"))
    downloads = os.path.join(ROOT, "downloads")
    if os.path.isdir(downloads):
        shutil.copytree(downloads, os.path.join(SITE, "downloads"))

    # Pygments theme appended to the stylesheet: dark code blocks everywhere.
    formatter = HtmlFormatter(style="monokai")
    with open(os.path.join(SITE, "static", "style.css"), "a") as f:
        f.write("\n" + formatter.get_style_defs(".highlight"))

    articles, pages = [], []
    for fname in sorted(os.listdir(CONTENT)):
        if not fname.endswith(".md"):
            continue
        with open(os.path.join(CONTENT, fname)) as f:
            meta, body = parse_front_matter(f.read())
        md = markdown.Markdown(extensions=MD_EXTENSIONS, extension_configs=MD_CONFIG)
        item = {
            "meta": meta,
            "html": md.convert(body),
            "minutes": reading_time(body),
            "slug": meta.get("slug", os.path.splitext(fname)[0]),
        }
        (articles if "date" in meta else pages).append(item)

    articles.sort(key=lambda a: a["meta"]["date"], reverse=True)

    for a in articles:
        page = page_shell(f'{a["meta"]["title"]} — {SITE_NAME}',
                          render_article(a["meta"], a["html"], a["minutes"]),
                          a["meta"].get("description", ""))
        with open(os.path.join(SITE, a["slug"] + ".html"), "w") as f:
            f.write(rebase(page))

    for p in pages:
        content = f'<article><h1>{html.escape(p["meta"]["title"])}</h1>{p["html"]}</article>'
        with open(os.path.join(SITE, p["slug"] + ".html"), "w") as f:
            f.write(rebase(page_shell(f'{p["meta"]["title"]} — {SITE_NAME}', content,
                                      p["meta"].get("description", ""))))

    # Index: hero + article list.
    cards = ""
    for a in articles:
        date = datetime.date.fromisoformat(a["meta"]["date"])
        cards += f"""<a class="card" href="/{a["slug"]}.html">
  <h2>{html.escape(a["meta"]["title"])}</h2>
  <p>{html.escape(a["meta"].get("description", ""))}</p>
  <p class="meta">{date.strftime("%B %-d, %Y")} &middot; {a["minutes"]} min read</p>
</a>\n"""
    hero = f"""<section class="hero">
  <h1>Run a recording studio from a Python script.</h1>
  <p>Real VST3 amp sims, hardware drum machine samples, sample instruments —
  driven headlessly from code, rendered to finished multitrack songs.
  Start with a self-contained NumPy/SciPy sketch, then explore the studio rigs.</p>
  <p class="hero-music">Two full albums came out the other end —
  <a href="/music.html">have a listen</a>.</p>
</section>
<section class="article-list">
{cards}</section>"""
    with open(os.path.join(SITE, "index.html"), "w") as f:
        f.write(rebase(page_shell(f"{SITE_NAME} — {SITE_TAGLINE}", hero)))

    # RSS feed.
    items = ""
    for a in articles:
        d = datetime.datetime.combine(datetime.date.fromisoformat(a["meta"]["date"]),
                                      datetime.time(12, 0))
        items += f"""<item>
<title>{html.escape(a["meta"]["title"])}</title>
<link>{SITE_URL}/{a["slug"]}.html</link>
<guid>{SITE_URL}/{a["slug"]}.html</guid>
<pubDate>{email.utils.format_datetime(d)}</pubDate>
<description>{html.escape(a["meta"].get("description", ""))}</description>
</item>\n"""
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>{SITE_NAME}</title>
<link>{SITE_URL}</link>
<description>{SITE_TAGLINE}</description>
{items}</channel></rss>"""
    with open(os.path.join(SITE, "feed.xml"), "w") as f:
        f.write(rss)

    n_book = build_book(SITE)

    print(f"Built {len(articles)} articles + {len(pages)} pages "
          f"+ {n_book} book pages -> {SITE}")

    # Deployment is deliberately separate from building.


if __name__ == "__main__":
    main()
