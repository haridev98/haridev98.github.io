# Haridev Sivaraman | Portfolio & Blog

Source for my personal website: **[haridevsivaraman.in](https://haridevsivaraman.in/)**

A fast, framework-free static site with a project showcase, resume, blog and contact form. It is hosted on GitHub Pages. The only build step is a small Python script that regenerates the blog list from a folder of posts.

## What's on the site

| Page | File | What it is |
| --- | --- | --- |
| Home | `index.html` | Intro, project carousel, blog list, contact form |
| Resume | `resume.html` and `resume.pdf` | Education, experience, skills and certifications, with a PDF download |
| Blog | `blog/` | Posts grouped by category, listed on the home page |
| 404 | `404.html` | "Page not found" page with a playable Snake game |

### Features

- Light and dark themes with an animated sun/moon toggle. The choice is remembered and shared across all pages through `localStorage`, and it follows the system setting on first visit.
- Responsive layout, with a bottom navigation bar on small screens.
- Smooth page-to-page view transitions, scroll-reveal animations and animated background. All of it respects `prefers-reduced-motion`.
- Blog list that is generated from files, so there is no hand-editing of HTML.
- Contact form powered by [Web3Forms](https://web3forms.com/), with a honeypot field for spam. A direct email link is shown as a fallback.
- SEO basics: canonical URLs, Open Graph and Twitter cards, JSON-LD structured data (`Person`, `ProfilePage`, breadcrumbs), `robots.txt` and `sitemap.xml`.
- No frameworks, bundlers or npm. Fonts come from Google Fonts and everything else is plain HTML, CSS and JavaScript.

## Repository layout

```
.
├── index.html            # home page (the blog list inside it is auto-generated)
├── resume.html           # resume page
├── resume.pdf            # downloadable resume
├── 404.html              # not-found page with a Snake game
├── IMG/                  # project screenshots used on the home page
├── blog/
│   ├── Python_and_DSA/   # one folder = one blog category
│   │   └── 22_10_2026_python_data_structures_handbook.html
│   ├── _links.json       # optional: external links (Medium etc.)
│   └── generated/        # created by build_blog.py for .md posts, do not edit
├── build_blog.py         # rebuilds the blog list in index.html
├── publish.sh            # build + commit + push in one command
├── BLOG_README.md        # full guide to writing and organising posts
├── CNAME                 # custom domain for GitHub Pages
├── .nojekyll             # stops GitHub Pages (Jekyll) from skipping files
├── robots.txt
├── sitemap.xml
└── .gitignore
```

`index.html`, `build_blog.py`, `publish.sh` and the `blog/` folder must stay together in the repository root.

## Running locally

The site is static, so any local web server works. Serve it from the repository root so that root-relative links (such as the `/` link on the 404 page) resolve correctly:

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

Opening `index.html` directly from disk also works for most pages, but the 404 page's home link and the browser's view transitions need a real server.

## Writing blog posts

The Blog section of `index.html` is generated from the `blog/` folder. The workflow is:

1. Add a post inside a category folder, such as `blog/Python_and_DSA/`.
2. Run `./publish.sh "Add my new post"`. It rebuilds the list, commits and pushes.
3. Wait a minute or two for GitHub Pages to update.

To rebuild without committing or pushing, run `python3 build_blog.py` (add `-v` for verbose output).

### Post files

Every post file is named `dd_mm_yyyy_name.ext`. The date is shown on the site and used for sorting, newest first.

| Type | Extension | Result |
| --- | --- | --- |
| HTML page | `.html` | Opens as it is. The title comes from `<title>` or the first `<h1>`. |
| Markdown | `.md` | Converted to a styled page in `blog/generated/`. Supports front matter (`title:`, `draft: true`). |
| External link | `.url` | First line is the URL, optional second line `title: ...`. Opens in a new tab. |

Many external links, such as Medium articles, can also be listed together in `blog/_links.json`. Folders and files starting with `_` or `.` are ignored, so `blog/_drafts/` is a safe place for work in progress.

Details such as `_category.json` (category title, description and order) and troubleshooting are in **[BLOG_README.md](BLOG_README.md)**.

### Link back to the home page

Posts live two folders below the site root (`blog/<category>/`), so a hand-written HTML post must link home with:

```html
<a href="../../index.html#blog">Back to home</a>
```

Markdown posts get the correct link automatically.

### Things to remember

- Never edit the blog list in `index.html` by hand. The block between `BLOG:START` and `BLOG:END` is overwritten on every build.
- Run the build before pushing. The site does not read `blog/` live; it shows whatever the last build wrote into `index.html`.
- Keep `.nojekyll` in the root, otherwise GitHub Pages can skip generated files.
- If the build finds no posts, it stops without touching `index.html`, so a mistake cannot blank the Blog section.
- `sitemap.xml` is maintained by hand. Add a `<url>` entry for each new post you want indexed.

## Requirements

- Python 3.9 or newer, standard library only (no `pip install` needed).
- Git, to use `publish.sh`.

## Deployment

The site is served by **GitHub Pages** from the repository root. `CNAME` points it at `haridevsivaraman.in`, and `.nojekyll` makes Pages serve files as they are. Pushing to the published branch deploys the site; `publish.sh` does the build and push for you.

## Projects featured

Highlights shown on the home page, each with source on GitHub:

- **YOLOv8 video annotation and model training app**: a Streamlit app for object detection with YOLOv8.
- **Otto Group product classification**: a tuned LightGBM classifier on 70,000+ records, top 30% on the Kaggle leaderboard.
- **Car evaluation with a feedforward neural network**: TensorFlow and Keras Tuner model reaching 92% accuracy.

## Contact

- Website: [haridevsivaraman.in](https://haridevsivaraman.in/)
- GitHub: [haridev98](https://github.com/haridev98)
- LinkedIn: [haridevsivaraman](https://www.linkedin.com/in/haridevsivaraman/)
- Medium: [@haridevsivaraman_65135](https://medium.com/@haridevsivaraman_65135)

---

© Haridev S. All rights reserved.
