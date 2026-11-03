#!/usr/bin/env python3
"""
build_blog.py  -  populate the Blog section of index.html from the blog/ folder.

Run it from the folder that contains index.html and blog/ :

    python build_blog.py

Folder layout
-------------
blog/
  python-data-structures/                  <- folder = blog category
    22_10_2026_python_data_structures_handbook.html   -> opens the HTML page
    05_11_2026_big_o_notes.md                        -> converted to a page automatically
    01_09_2026_python_tips.url                       -> external link (Medium etc.)
    _category.json                                   -> optional: title / desc / order
  _links.json                              <- optional: external links for ANY category

File names are  dd_mm_yyyy_name.(html|md|url).  The date is the "published" date shown
next to the post and used for sorting (newest first).

Optional files
--------------
_category.json (inside a category folder)
    {"title": "Python & Data Structures", "desc": "One line description", "order": 1}

*.url (inside a category folder; plain text)
    https://medium.com/@you/my-article
    title: My article title            <- optional, else made from the file name

_links.json (in blog/ ; add Medium posts to an existing OR a brand new category)
    [
      {"category": "Python & Data Structures", "title": "My Medium article",
       "date": "01_09_2026", "url": "https://medium.com/@you/my-article"}
    ]
    "category" may be a folder name or a category title. If it matches nothing,
    a new category is created.

The blog/generated/ folder is created by this script - do not put your own posts there.
Folders / files starting with "_" or "." are ignored (so you can park drafts there).
In .md files you can add front matter:  ---\ntitle: ...\ndraft: true\n---

Logging
-------
Every step is printed with a time stamp and a level (INFO / OK / WARN / ERROR / FAIL).
    python build_blog.py -v             extra detail (ignored files, link targets)
    python build_blog.py --allow-empty  write index.html even if no posts are found
If no posts are found the script stops WITHOUT touching index.html, so a mistake can never
blank the Blog section. Exit code 0 = success, 1 = nothing written (see the FAIL line).
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

ROOT = Path(__file__).resolve().parent
BLOG_DIR = ROOT / "blog"
BUILD_DIR = BLOG_DIR / "generated"       # generated pages for .md files (safe to delete; no "_" prefix so GitHub Pages/Jekyll serves it)
INDEX = ROOT / "index.html"
SITE_NAME = "Haridev Sivaraman"

NAME_RE = re.compile(r"^(\d{2})_(\d{2})_(\d{4})_(.+)\.(html?|md|markdown|url)$", re.I)
START, END = "/* BLOG:START", "/* BLOG:END */"

warnings = []
errors = []
VERBOSE = False


# --------------------------------------------------------------------------- logging
def _out(level, msg):
    # flush=True so lines appear live even when run through publish.sh / a pipe (Git Bash, VS Code, CI)
    print("[%s] %-5s %s" % (datetime.now().strftime("%H:%M:%S"), level, msg), flush=True)


def log(msg):
    _out("INFO", msg)


def ok(msg):
    _out("OK", msg)


def debug(msg):
    if VERBOSE:
        _out("DEBUG", msg)


def warn(msg):
    warnings.append(msg)
    _out("WARN", msg)


def error(msg):
    errors.append(msg)
    _out("ERROR", msg)


def fatal(msg):
    error(msg)
    _out("FAIL", "Stopped. index.html was NOT modified.")
    sys.exit(1)


def step(n, total, title):
    print("", flush=True)
    print("==> [%d/%d] %s" % (n, total, title), flush=True)


# --------------------------------------------------------------------------- helpers
def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower().replace("&", "and")).strip("-")


def humanize(s):
    s = re.sub(r"[_\-]+", " ", s).strip()
    return " ".join(w if w.isupper() else w[:1].upper() + w[1:] for w in s.split())


def parse_date(s):
    s = str(s).strip()
    m = re.match(r"^(\d{1,2})[_\-/.](\d{1,2})[_\-/.](\d{4})$", s)
    if m:
        d, mo, y = int(m[1]), int(m[2]), int(m[3])
    else:
        m = re.match(r"^(\d{4})[_\-/.](\d{1,2})[_\-/.](\d{1,2})$", s)
        if not m:
            return None
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def http_url(u):
    u = str(u).strip()
    return u if re.match(r"^https?://", u, re.I) else None


def web_path(p):
    return "/".join(quote(part) for part in Path(os.path.relpath(p, ROOT)).parts)


def title_from_html(text, fallback):
    for pat in (r"<title[^>]*>(.*?)</title>", r"<h1[^>]*>(.*?)</h1>"):
        m = re.search(pat, text, re.I | re.S)
        if m:
            t = html.unescape(re.sub(r"<[^>]+>", "", m[1]))
            t = re.sub(r"\s+", " ", t).strip()
            if t:
                return t
    return fallback


# --------------------------------------------------------------------------- markdown
def split_front_matter(text):
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if m:
        for line in m[1].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip().strip("\"'")
        text = text[m.end():]
    return meta, text


def md_to_html(text, src_dir, out_dir):
    def fix(u):
        u = html.unescape(u.strip())
        sm = re.match(r"^([a-z][a-z0-9+.-]*):", u, re.I)
        if sm and sm[1].lower() not in ("http", "https", "mailto"):
            return "#"
        if not sm and not u.startswith(("#", "/", "//")):
            rel = os.path.relpath(os.path.join(src_dir, u), out_dir).replace(os.sep, "/")
            u = quote(rel, safe="/#?=&%")
        return html.escape(u, quote=True)

    def emph(t):
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![\w])__(.+?)__(?![\w])", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
        t = re.sub(r"(?<![\w])_(?!\s)(.+?)(?<!\s)_(?![\w])", r"<em>\1</em>", t)
        return re.sub(r"~~(.+?)~~", r"<del>\1</del>", t)

    def inline(s):
        s = html.escape(s, quote=False)
        stash = []

        def keep(h):
            stash.append(h)
            return "\x00%d\x00" % (len(stash) - 1)

        s = re.sub(r"`([^`]+)`", lambda m: keep("<code>%s</code>" % m[1]), s)
        s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)",
                   lambda m: keep('<img src="%s" alt="%s" loading="lazy">'
                                  % (fix(m[2]), m[1].replace('"', "&quot;"))), s)

        def link(m):
            href = fix(m[2])
            ext = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
            return keep('<a href="%s"%s>%s</a>' % (href, ext, emph(m[1])))

        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)[^)]*\)", link, s)
        s = emph(s)
        while "\x00" in s:
            s = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m[1])], s)
        return s

    item_re = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")

    def render_list(lines):
        base = len(item_re.match(lines[0])[1])
        ordered = lines[0].strip()[0].isdigit()
        items, cur = [], None
        for ln in lines:
            m = item_re.match(ln)
            if m and len(m[1]) <= base:
                cur = [m[3], []]
                items.append(cur)
            elif cur is not None:
                cur[1].append(ln)
        out = []
        for first, kids in items:
            sub = [k for k in kids if k.strip()]
            nested = [k for k in sub if item_re.match(k)]
            body = inline(first)
            if nested:
                start = next(i for i, k in enumerate(sub) if item_re.match(k))
                extra = " ".join(k.strip() for k in sub[:start])
                body += (" " + inline(extra) if extra else "") + render_list(sub[start:])
            elif sub:
                body += " " + inline(" ".join(k.strip() for k in sub))
            out.append("<li>%s</li>" % body)
        tag = "ol" if ordered else "ul"
        return "<%s>%s</%s>" % (tag, "".join(out), tag)

    sep_re = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")

    def cells(ln):
        return [c.strip() for c in ln.strip().strip("|").split("|")]

    def block(src):
        lines = src.splitlines()
        out, para, i = [], [], 0

        def flush():
            if para:
                out.append("<p>%s</p>" % inline(" ".join(x.strip() for x in para)))
                para.clear()

        while i < len(lines):
            ln = lines[i]
            st = ln.strip()
            if st.startswith("```"):
                flush()
                lang = re.sub(r"[^\w+\-]", "", st[3:])
                buf, i = [], i + 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    buf.append(lines[i])
                    i += 1
                i += 1
                cls = ' class="language-%s"' % lang if lang else ""
                out.append("<pre><code%s>%s</code></pre>" % (cls, html.escape("\n".join(buf))))
                continue
            m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", st)
            if m:
                flush()
                n = len(m[1])
                out.append('<h%d id="%s">%s</h%d>' % (n, slug(re.sub(r"[`*_]", "", m[2])), inline(m[2]), n))
                i += 1
                continue
            if re.match(r"^([-*_])(\s*\1){2,}$", st):
                flush(); out.append("<hr>"); i += 1; continue
            if st.startswith(">"):
                flush()
                buf = []
                while i < len(lines) and lines[i].strip().startswith(">"):
                    buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
                out.append("<blockquote>%s</blockquote>" % block("\n".join(buf)))
                continue
            if item_re.match(ln):
                flush()
                buf = []
                while i < len(lines) and lines[i].strip() and (item_re.match(lines[i]) or lines[i].startswith((" ", "\t"))):
                    buf.append(lines[i]); i += 1
                out.append(render_list(buf))
                continue
            if "|" in st and i + 1 < len(lines) and sep_re.match(lines[i + 1]):
                flush()
                head = cells(ln); i += 2; rows = []
                while i < len(lines) and "|" in lines[i] and lines[i].strip():
                    rows.append(cells(lines[i])); i += 1
                t = "<table><thead><tr>%s</tr></thead><tbody>" % "".join("<th>%s</th>" % inline(c) for c in head)
                t += "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r) for r in rows)
                out.append(t + "</tbody></table>")
                continue
            if not st:
                flush(); i += 1; continue
            para.append(ln); i += 1
        flush()
        return "\n".join(out)

    return block(text)


PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | {site}</title>
<meta name="author" content="{site}">
<script>try{{var t=localStorage.getItem("theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
<style>
:root{{--bg:#F5F7FA;--surface:#fff;--ink:#14213D;--muted:#5B6578;--line:#D9DEE8;--signal:#2F5BEA;--code:#EEF1F7}}
@media(prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#0E1626;--surface:#16213A;--ink:#E8ECF5;--muted:#9AA6BF;--line:#2A3858;--signal:#7FA2FF;--code:#1B2849}}}}
:root[data-theme=dark]{{--bg:#0E1626;--surface:#16213A;--ink:#E8ECF5;--muted:#9AA6BF;--line:#2A3858;--signal:#7FA2FF;--code:#1B2849}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.7 "IBM Plex Sans",system-ui,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:32px 20px 80px}}
.back a{{color:var(--signal);text-decoration:none;font-weight:600}}
h1{{font:700 2.1rem/1.2 "Newsreader",Georgia,serif;margin:.6em 0 .2em}}
.meta{{color:var(--muted);margin:0 0 1.6em;font-size:.95rem}}
h2,h3,h4{{line-height:1.3;margin:1.8em 0 .5em}}
a{{color:var(--signal)}} img{{max-width:100%;height:auto;border-radius:8px}}
code{{background:var(--code);padding:.1em .35em;border-radius:5px;font-size:.9em}}
pre{{background:var(--code);padding:14px 16px;border-radius:10px;overflow-x:auto;line-height:1.5}}
pre code{{background:none;padding:0}}
blockquote{{margin:1em 0;padding:.1em 1em;border-left:4px solid var(--signal);color:var(--muted)}}
table{{border-collapse:collapse;display:block;overflow-x:auto}} th,td{{border:1px solid var(--line);padding:6px 12px;text-align:left}}
hr{{border:0;border-top:1px solid var(--line);margin:2em 0}}
</style></head><body><main>
<p class="back"><a href="{back}">&larr; Back to blog</a></p>
<article><h1>{title}</h1><p class="meta">{when}</p>
{body}
</article></main></body></html>
"""


# --------------------------------------------------------------------------- scan
POST_EXT = (".html", ".htm", ".md", ".markdown", ".url")
QUIET_FILES = {"thumbs.db", "desktop.ini"}          # OS clutter, never worth a warning
BLOCK_RE = re.compile(r"const BLOG\s*=\s*(.*);\s*\Z", re.S)
LIST_RE = re.compile(r'(<div class="cats" id="post-list">)(.*?)(</div>)(?=\s*</section>)', re.S)


def rel(p):
    """Path relative to the site root, with forward slashes (for readable log lines)."""
    try:
        return Path(os.path.relpath(p, ROOT)).as_posix()
    except ValueError:                               # different drive on Windows
        return str(p)


def read_text(path):
    """Read a text file as UTF-8. Strips a BOM (Windows Notepad adds one), normalises
    line endings, and falls back to Windows-1252 for 'ANSI' files instead of crashing."""
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        warn("%s is not valid UTF-8 - read it as Windows-1252. Re-save it as UTF-8 to be safe." % rel(path))
        text = raw.decode("cp1252", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def new_cat(title, folder=None):
    return {"key": slug(folder or title), "category": title, "desc": "", "order": 999, "posts": [], "aliases": {slug(title)}}


def process_file(folder, f, c):
    """Handle one file inside a category folder. Returns 'post', 'skipped' or 'asset'."""
    label = "%s/%s" % (folder.name, f.name)
    m = NAME_RE.match(f.name)
    if not m:
        if f.suffix.lower() in POST_EXT:
            warn("skipped %s  (name must be dd_mm_yyyy_name%s, e.g. 22_10_2026_my_post%s)"
                 % (label, f.suffix.lower(), f.suffix.lower()))
            return "skipped"
        if any(s.lower() in POST_EXT for s in f.suffixes[:-1]):
            warn("skipped %s  (double extension - on Windows, turn on 'File name extensions' in Explorer "
                 "and rename it so it ends in .html, .md or .url)" % label)
            return "skipped"
        debug("ignored %s  (not a post file - treated as an image/script/asset)" % label)
        return "asset"

    d = parse_date("%s_%s_%s" % m.group(1, 2, 3))
    if not d:
        warn("skipped %s  (invalid date %s_%s_%s)" % ((label,) + m.group(1, 2, 3)))
        return "skipped"

    stem, ext = m[4], m[5].lower()
    fallback = humanize(stem)
    post = {"date": d.isoformat()}

    if ext in ("html", "htm"):
        post["title"] = title_from_html(read_text(f), fallback)
        post["url"] = web_path(f)
        kind, note = "html", label
    elif ext in ("md", "markdown"):
        meta, body = split_front_matter(read_text(f))
        if meta.get("draft", "").lower() in ("true", "yes", "1"):
            log("  - draft hidden: %s  (front matter has draft: true)" % label)
            return "skipped"
        h1 = re.match(r"^\s*#\s+(.+?)\s*#*\s*(?:\n|$)", body)
        title = meta.get("title") or (h1[1].strip() if h1 else fallback)
        if h1:
            body = body[h1.end():]
        out_dir = BUILD_DIR / folder.name
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / (f.stem + ".html")
        page = PAGE.format(
            title=html.escape(title), site=SITE_NAME, when=d.strftime("%d %b %Y"),
            back="../../../index.html#blog",
            body=md_to_html(body, str(f.parent), str(out_dir)))
        out.write_text(page, encoding="utf-8")
        debug("generated %s (%d bytes)" % (rel(out), len(page.encode("utf-8"))))
        post["title"] = title
        post["url"] = web_path(out)
        kind, note = "md", "%s -> %s" % (label, rel(out))
    else:  # .url
        url, title = None, fallback
        for line in read_text(f).splitlines():
            line = line.strip()
            if line.lower().startswith("title:"):
                title = line[6:].strip() or title
            elif http_url(line) and not url:
                url = line
        if not url:
            warn("skipped %s  (no http(s) URL inside)" % label)
            return "skipped"
        post.update(title=title, url=url, external=True)
        kind, note = "url", "%s -> %s" % (label, url)

    c["posts"].append(post)
    log("  + %-4s %s  %s   [%s]" % (kind, post["date"], post["title"], note))
    debug("link target: %s" % post["url"])
    return "post"


def scan():
    log("Blog folder: %s" % BLOG_DIR)
    if not BLOG_DIR.is_dir():
        fatal("blog/ folder not found. It must sit next to build_blog.py, expected: %s" % BLOG_DIR)
    if BUILD_DIR.exists():
        log("Cleaning old generated pages: %s" % rel(BUILD_DIR))
        try:
            shutil.rmtree(BUILD_DIR)
        except OSError as e:
            fatal("could not delete %s (%s). Close any program that has files open in it." % (rel(BUILD_DIR), e))

    cats = {}      # key -> category
    alias = {}     # slug -> key

    def register(c):
        cats[c["key"]] = c
        for a in c["aliases"] | {c["key"]}:
            alias[a] = c["key"]

    entries = sorted(BLOG_DIR.iterdir(), key=lambda p: p.name.lower())
    log("Found %d item(s) directly inside blog/: %s" % (len(entries), ", ".join(p.name for p in entries) or "(empty)"))

    folders = []
    for p in entries:
        if p.name == "_links.json":
            continue
        if p.name.startswith(("_", ".")):
            log("  ignored %s  (names starting with _ or . are skipped on purpose)" % p.name)
        elif p.is_dir():
            folders.append(p)
        elif p.name.lower() not in QUIET_FILES:
            warn("blog/%s is a loose file - posts must live inside a category folder, "
                 "e.g. blog/my-category/%s" % (p.name, p.name))
    if not folders:
        warn("no category folders found inside blog/ - create blog/<category>/ and put posts in it")
    else:
        log("Category folders: %s" % ", ".join(p.name for p in folders))

    for folder in folders:
        c = new_cat(humanize(folder.name), folder.name)
        log("Category folder: %s/" % folder.name)
        meta_file = folder / "_category.json"
        if meta_file.exists():
            try:
                meta = json.loads(read_text(meta_file))
                c["category"] = meta.get("title", c["category"])
                c["desc"] = meta.get("desc", "")
                c["order"] = meta.get("order", 999)
                c["aliases"].add(slug(c["category"]))
                log("  _category.json: title=%r order=%s" % (c["category"], c["order"]))
            except (ValueError, OSError, AttributeError) as e:
                warn("%s: bad _category.json (%s)" % (folder.name, e))
        else:
            log("  title: %r (made from the folder name; no _category.json)" % c["category"])
        register(c)

        tally = {"post": 0, "skipped": 0, "asset": 0}
        for f in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            if f.name.startswith(("_", ".")) or f.name.lower() in QUIET_FILES:
                debug("ignored %s/%s  (starts with _ or .)" % (folder.name, f.name))
                continue
            if f.is_dir():
                warn("%s/%s/ is a sub-folder - only one folder level is read, its contents are ignored" % (folder.name, f.name))
                tally["skipped"] += 1
                continue
            try:
                tally[process_file(folder, f, c)] += 1
            except Exception as e:          # one bad file must not hide problems in the others
                error("could not process %s/%s: %s: %s" % (folder.name, f.name, type(e).__name__, e))
        log("  = %d post(s), %d skipped, %d other file(s) ignored" % (tally["post"], tally["skipped"], tally["asset"]))

    # external links from blog/_links.json
    lf = BLOG_DIR / "_links.json"
    if lf.exists():
        log("Reading blog/_links.json")
        try:
            data = json.loads(read_text(lf))
            data = data.get("links", []) if isinstance(data, dict) else data
        except (ValueError, OSError) as e:
            warn("bad _links.json (%s)" % e)
            data = []
        for n, item in enumerate(data, 1):
            if not isinstance(item, dict):
                warn("_links.json entry #%d is not an object" % n)
                continue
            url, d = http_url(item.get("url", "")), parse_date(item.get("date", ""))
            if not url or not item.get("title") or not d:
                warn("_links.json entry #%d needs title, url (http/https) and date" % n)
                continue
            name = item.get("category") or "More posts"
            key = alias.get(slug(name))
            if key is None:
                c = new_cat(name)
                register(c)
                key = c["key"]
                log("  new category created from _links.json: %r" % name)
            cats[key]["posts"].append({"title": item["title"], "date": d.isoformat(), "url": url, "external": True})
            log("  + link %s  %s   [category: %s]" % (d.isoformat(), item["title"], cats[key]["category"]))
    else:
        debug("no blog/_links.json (optional)")

    result = []
    for c in cats.values():
        if not c["posts"]:
            log("Category %r has no visible posts - it will not be shown on the site" % c["category"])
            continue
        c["posts"].sort(key=lambda p: (p["date"], p["title"].lower()), reverse=True)
        for p in c["posts"]:
            if p.get("external"):
                p["source"] = (urlparse(p["url"]).hostname or "").removeprefix("www.")
            p.pop("aliases", None)
        result.append(c)
    result.sort(key=lambda c: (c["order"], tuple(-int(x) for x in c["posts"][0]["date"].split("-")), c["category"].lower()))
    return [{"category": c["category"], "desc": c["desc"], "posts": c["posts"]} for c in result]


# --------------------------------------------------------------------------- write index.html
def esc(s):
    return html.escape(str(s), quote=True)


def safe_href(u):
    return esc(u if re.match(r"^(https?:|mailto:)", u, re.I) or not re.match(r"^[a-z][a-z0-9+.-]*:", u, re.I) else "#")


def prerender(blog):
    out = []
    for i, c in enumerate(blog):
        n = len(c["posts"])
        lis = []
        for p in c["posts"]:
            ext = p.get("external")
            attrs = ' target="_blank" rel="noopener"' if ext else ""
            arrow = ' <i class="x" aria-hidden="true">↗</i>' if ext else ""
            meta = p["date"] + (" · " + p["source"] if ext and p.get("source") else "")
            lis.append('<li><a href="%s"%s><b class="t">%s%s</b><span>%s</span></a></li>'
                       % (safe_href(p["url"]), attrs, esc(p["title"]), arrow, esc(meta)))
        out.append('<details class="cat"%s><summary>%s<span class="n">%d %s</span></summary>%s<ul>%s</ul></details>'
                   % (" open" if i == 0 else "", esc(c["category"]), n, "post" if n == 1 else "posts",
                      '<p class="desc">%s</p>' % esc(c["desc"]) if c["desc"] else "", "".join(lis)))
    return "".join(out)


def parse_block(block):
    """Return the BLOG list stored between the markers, or None if it can't be read."""
    m = BLOCK_RE.search(block)
    if not m:
        return None
    try:
        return json.loads(m[1])
    except ValueError:
        return None


def count_posts(blog):
    return sum(len(c["posts"]) for c in blog)


def update_index(blog):
    log("Reading %s" % rel(INDEX))
    if not INDEX.is_file():
        fatal("index.html not found, expected: %s" % INDEX)
    text = read_text(INDEX)
    s, e = text.find(START), text.find(END)
    if s < 0 or e < 0:
        fatal("BLOG:START / BLOG:END markers not found in index.html (use the supplied index.html: "
              "the script block must contain '/* BLOG:START' and '/* BLOG:END */')")
    if e < s:
        fatal("BLOG:END comes before BLOG:START in index.html")
    line = lambda pos: text.count("\n", 0, pos) + 1
    log("  markers found: BLOG:START at line %d, BLOG:END at line %d" % (line(s), line(e)))

    old = parse_block(text[s:e])
    if old is None:
        log("  previous BLOG data could not be read (first run or edited by hand) - it will be replaced")
    else:
        log("  previous BLOG data: %d post(s) in %d categor%s" % (count_posts(old), len(old), "y" if len(old) == 1 else "ies"))

    js = json.dumps(blog, indent=2, ensure_ascii=False).replace("</", "<\\/")
    block = START + " (auto-generated by build_blog.py - do not edit by hand) */\nconst BLOG = " + js + ";\n" + END
    new = text[:s] + block + text[e + len(END):]
    log("  BLOG data rebuilt: %d post(s) in %d categor%s" % (count_posts(blog), len(blog), "y" if len(blog) == 1 else "ies"))

    new, k = LIST_RE.subn(lambda m: m[1] + prerender(blog) + m[3], new, count=1)
    if k:
        log("  pre-rendered list (#post-list) refreshed")
    else:
        warn("could not find #post-list to prerender (the JS will still render it from BLOG)")

    if new == text:
        log("index.html is already up to date - nothing written")
        return
    INDEX.write_text(new, encoding="utf-8")
    ok("index.html written (%d -> %d bytes)" % (len(text.encode("utf-8")), len(new.encode("utf-8"))))


def verify(blog):
    """Re-read index.html from disk and check that what a visitor will see matches what we built."""
    text = read_text(INDEX)
    s, e = text.find(START), text.find(END)
    data = parse_block(text[s:e]) if 0 <= s < e else None
    if data is None:
        error("verify: the BLOG data in index.html cannot be read back")
        return
    want = count_posts(blog)
    got_js = count_posts(data)
    m = LIST_RE.search(text)
    got_html = m[2].count("<li>") if m else None
    log("  posts expected: %d | in BLOG data: %d | in pre-rendered list: %s"
        % (want, got_js, got_html if got_html is not None else "n/a"))
    if got_js != want:
        error("verify: BLOG data holds %d post(s) but %d were built" % (got_js, want))
    if got_html is not None and got_html != want:
        error("verify: pre-rendered list shows %d post(s) but %d were built" % (got_html, want))

    missing = 0
    for c in data:
        for p in c["posts"]:
            if p.get("external"):
                continue
            target = ROOT / unquote(p["url"].split("#")[0].split("?")[0])
            if not target.is_file():
                missing += 1
                warn("link target missing on disk: %s  (post %r would give a 404)" % (p["url"], p["title"]))
    if not missing:
        log("  all local post links point to files that exist")
    if not (ROOT / ".nojekyll").exists():
        warn(".nojekyll is missing in the repo root - GitHub Pages may skip blog/generated/ (publish.sh creates it)")


# --------------------------------------------------------------------------- main
def main(argv=None):
    global VERBOSE
    ap = argparse.ArgumentParser(description="Rebuild the Blog section of index.html from the blog/ folder.")
    ap.add_argument("-v", "--verbose", action="store_true", help="show extra detail (ignored files, link targets)")
    ap.add_argument("--allow-empty", action="store_true",
                    help="write index.html even when no posts were found (normally this is refused)")
    args = ap.parse_args(argv)
    VERBOSE = args.verbose

    for stream in (sys.stdout, sys.stderr):      # Windows consoles: never crash on a non-ASCII title
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    t0 = time.time()
    print("=" * 64)
    print(" build_blog.py  |  %s" % datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    print("=" * 64, flush=True)
    log("Python %s (%s) on %s" % (sys.version.split()[0], sys.executable, sys.platform))
    log("Site root: %s" % ROOT)
    if Path.cwd().resolve() != ROOT:
        log("Working directory is %s (paths below are still relative to the site root)" % Path.cwd())
    log("Verbose logging: %s" % ("on" if VERBOSE else "off (use -v for more)"))

    step(1, 3, "Scanning blog/")
    blog = scan()
    total = count_posts(blog)
    external = sum(1 for c in blog for p in c["posts"] if p.get("external"))

    if errors:
        print("", flush=True)
        _out("FAIL", "%d error(s) above - index.html was NOT modified. Fix them and run again." % len(errors))
        return 1

    if total == 0 and not args.allow_empty:
        print("", flush=True)
        _out("FAIL", "No posts were found, so index.html was NOT modified (writing now would blank the Blog section).")
        log("Checklist:")
        log("  1. Posts must sit inside a category folder:  blog/<category>/dd_mm_yyyy_name.html | .md | .url")
        log("     (files placed directly in blog/ are ignored)")
        log("  2. File names need a valid date, e.g. 22_10_2026_my_post.html (day_month_year, underscores)")
        log("  3. In Windows Explorer, turn on 'File name extensions' to rule out names like post.html.txt")
        log("  4. Markdown posts with 'draft: true' are hidden on purpose")
        log("  5. Read the WARN lines above - each skipped file says why")
        log("Run with --allow-empty if you really want an empty blog.")
        return 1

    step(2, 3, "Updating index.html")
    update_index(blog)

    step(3, 3, "Verifying result")
    verify(blog)

    print("", flush=True)
    log("Summary")
    for c in blog:
        log("  %-34s %d post(s)" % (c["category"], len(c["posts"])))
    if errors:
        _out("FAIL", "%d error(s) - check the lines above." % len(errors))
        return 1
    ok("Done: %d post(s) in %d categor%s (%d external), %d warning(s), %.2fs"
       % (total, len(blog), "y" if len(blog) == 1 else "ies", external, len(warnings), time.time() - t0))
    if warnings:
        log("Warnings (the site was still updated):")
        for w in warnings:
            log("  ! " + w)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        _out("FAIL", "Unexpected crash - full details below")
        traceback.print_exc()
        sys.exit(1)
