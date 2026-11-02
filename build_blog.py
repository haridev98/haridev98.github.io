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
"""
import html
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent
BLOG_DIR = ROOT / "blog"
BUILD_DIR = BLOG_DIR / "generated"       # generated pages for .md files (safe to delete; no "_" prefix so GitHub Pages/Jekyll serves it)
INDEX = ROOT / "index.html"
SITE_NAME = "Haridev Sivaraman"

NAME_RE = re.compile(r"^(\d{2})_(\d{2})_(\d{4})_(.+)\.(html?|md|markdown|url)$", re.I)
START, END = "/* BLOG:START", "/* BLOG:END */"

warnings = []


def warn(msg):
    warnings.append(msg)
    print("  ! " + msg)


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
def new_cat(title, folder=None):
    return {"key": slug(folder or title), "category": title, "desc": "", "order": 999, "posts": [], "aliases": {slug(title)}}


def scan():
    if not BLOG_DIR.is_dir():
        sys.exit("blog/ folder not found next to build_blog.py")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    cats = {}      # key -> category
    alias = {}     # slug -> key

    def register(c):
        cats[c["key"]] = c
        for a in c["aliases"] | {c["key"]}:
            alias[a] = c["key"]

    for folder in sorted(p for p in BLOG_DIR.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")) and p != BUILD_DIR):
        c = new_cat(humanize(folder.name), folder.name)
        meta_file = folder / "_category.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                c["category"] = meta.get("title", c["category"])
                c["desc"] = meta.get("desc", "")
                c["order"] = meta.get("order", 999)
                c["aliases"].add(slug(c["category"]))
            except (ValueError, OSError) as e:
                warn("%s: bad _category.json (%s)" % (folder.name, e))
        register(c)

        for f in sorted(folder.iterdir()):
            if not f.is_file() or f.name.startswith(("_", ".")):
                continue
            m = NAME_RE.match(f.name)
            if not m:
                if f.suffix.lower() in (".html", ".htm", ".md", ".markdown", ".url"):
                    warn("skipped %s/%s  (name must be dd_mm_yyyy_name.ext)" % (folder.name, f.name))
                continue
            d = parse_date("%s_%s_%s" % m.group(1, 2, 3))
            if not d:
                warn("skipped %s/%s  (invalid date)" % (folder.name, f.name))
                continue
            stem, ext = m[4], m[5].lower()
            fallback = humanize(stem)
            post = {"date": d.isoformat()}

            if ext in ("html", "htm"):
                post["title"] = title_from_html(f.read_text(encoding="utf-8", errors="ignore"), fallback)
                post["url"] = web_path(f)
            elif ext in ("md", "markdown"):
                meta, body = split_front_matter(f.read_text(encoding="utf-8"))
                if meta.get("draft", "").lower() in ("true", "yes", "1"):
                    continue
                h1 = re.match(r"^\s*#\s+(.+?)\s*#*\s*(?:\n|$)", body)
                title = meta.get("title") or (h1[1].strip() if h1 else fallback)
                if h1:
                    body = body[h1.end():]
                out_dir = BUILD_DIR / folder.name
                out_dir.mkdir(parents=True, exist_ok=True)
                out = out_dir / (f.stem + ".html")
                out.write_text(PAGE.format(
                    title=html.escape(title), site=SITE_NAME, when=d.strftime("%d %b %Y"),
                    back="../../../index.html#blog",
                    body=md_to_html(body, str(f.parent), str(out_dir))), encoding="utf-8")
                post["title"] = title
                post["url"] = web_path(out)
            else:  # .url
                url, title = None, fallback
                for line in f.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.lower().startswith("title:"):
                        title = line[6:].strip() or title
                    elif http_url(line) and not url:
                        url = line
                if not url:
                    warn("skipped %s/%s  (no http(s) URL inside)" % (folder.name, f.name))
                    continue
                post.update(title=title, url=url, external=True)
            c["posts"].append(post)

    # external links from blog/_links.json
    lf = BLOG_DIR / "_links.json"
    if lf.exists():
        try:
            data = json.loads(lf.read_text(encoding="utf-8"))
            data = data.get("links", []) if isinstance(data, dict) else data
        except (ValueError, OSError) as e:
            warn("bad _links.json (%s)" % e)
            data = []
        for n, item in enumerate(data, 1):
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
            cats[key]["posts"].append({"title": item["title"], "date": d.isoformat(), "url": url, "external": True})

    result = []
    for c in cats.values():
        if not c["posts"]:
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


def update_index(blog):
    text = INDEX.read_text(encoding="utf-8")
    s, e = text.find(START), text.find(END)
    if s < 0 or e < 0:
        sys.exit("BLOG:START / BLOG:END markers not found in index.html (use the supplied index.html)")
    js = json.dumps(blog, indent=2, ensure_ascii=False).replace("</", "<\\/")
    block = START + " (auto-generated by build_blog.py - do not edit by hand) */\nconst BLOG = " + js + ";\n" + END
    text = text[:s] + block + text[e + len(END):]
    text, k = re.subn(r'(<div class="cats" id="post-list">).*?(</div>)(?=\s*</section>)',
                      lambda m: m[1] + prerender(blog) + m[2], text, count=1, flags=re.S)
    if not k:
        warn("could not find #post-list to prerender (the JS will still render it)")
    INDEX.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    print("Scanning blog/ ...")
    blog = scan()
    update_index(blog)
    total = sum(len(c["posts"]) for c in blog)
    ext = sum(1 for c in blog for p in c["posts"] if p.get("external"))
    for c in blog:
        print("  %-34s %d post(s)" % (c["category"], len(c["posts"])))
    print("Done: %d posts in %d categories (%d external)%s" %
          (total, len(blog), ext, ", %d warning(s)" % len(warnings) if warnings else ""))
