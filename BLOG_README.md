# Blog guide

The Blog section of `index.html` is generated from the `blog/` folder by `build_blog.py`.
You add files, run one command, and the list on the site updates itself.

## Quick start

1. Put your post file in the right category folder under `blog/` (see below).
2. Run `./publish.sh "Add my new post"` (builds the list, commits and pushes).
3. Wait a minute or two for GitHub Pages to update.

To build without pushing: `python build_blog.py`.

## Repo layout

```
your-repo/
  index.html
  build_blog.py
  publish.sh
  .nojekyll
  blog/
    python-data-structures/                  <- one folder = one category
      22_10_2026_python_data_structures_handbook.html
      05_11_2026_big_o_notes.md
      01_09_2026_python_tips.url
      _category.json                         <- optional
    mlops/
      10_08_2026_model_drift.url
    _links.json                              <- optional
    _drafts/                                 <- ignored (starts with "_")
    generated/                               <- created by the script, do not edit
```

`build_blog.py`, `publish.sh` and `index.html` must stay in the same folder as `blog/`.

## Rules

### Categories

- Each folder directly inside `blog/` is a category shown in the Blog section.
- The title comes from the folder name: `python-data-structures` becomes **Python Data Structures**.
- Only one level is read. Do not nest folders inside a category folder.
- Folders and files starting with `_` or `.` are ignored.
- `blog/generated/` is created by the script. Do not put your own posts in it.

### Post file names

Every post must be named:

```
dd_mm_yyyy_name.ext
```

| Part   | Meaning                                                              |
| ------ | -------------------------------------------------------------------- |
| `dd_mm_yyyy` | Publish date. Shown next to the post and used to sort (newest first). |
| `name` | Used for the URL, and for the title if none is found inside the file. |
| `ext`  | `html`, `md` or `url`                                                |

Examples: `22_10_2026_python_data_structures_handbook.html`, `05_11_2026_big_o_notes.md`

A file with a wrong name or an impossible date (such as `31_02_2026`) is skipped, and the script prints a warning.

## Post types

### 1. HTML post (`.html`)

A complete HTML page. The post opens as it is.

- The title is read from `<title>`, or from the first `<h1>` if there is no `<title>`.
- Images and scripts used by the page should be placed next to it in the same category folder, or referenced by a path that works from the site root.

### 2. Markdown post (`.md`)

The script converts it into a styled page in `blog/generated/` automatically.

```markdown
---
title: Big-O Notes
draft: false
---
# Big-O Notes

Your content here.
```

- Title: `title:` in the front matter, otherwise the first `# heading`, otherwise the file name.
- The first `# heading` is removed from the body, because the page shows the title itself.
- `draft: true` hides the post from the site.
- Supported: headings, paragraphs, bold, italic, inline code, code blocks, links, images, lists (including nested), tables, quotes and horizontal rules.
- Images: use a path relative to the `.md` file, for example `![diagram](img/flow.png)`.

### 3. External link (`.url`), for Medium or other sites

A plain text file. The first line is the URL. An optional second line sets the title.

```
https://medium.com/@yourname/your-article
title: My Article on Medium
```

- Without a `title:` line, the title is made from the file name.
- The link opens in a new tab and shows a `↗` and the site name (for example `2026-09-01 · medium.com`).
- Only `http://` and `https://` links are accepted.

### 4. Many external links in one file (`blog/_links.json`)

Use this to add Medium posts to any category, including one that has no files of its own.

```json
[
  {
    "category": "Python & Data Structures",
    "title": "Python tips on Medium",
    "date": "01_09_2026",
    "url": "https://medium.com/@yourname/python-tips"
  },
  {
    "category": "LLM Notes",
    "title": "RAG explained",
    "date": "02_10_2026",
    "url": "https://medium.com/@yourname/rag"
  }
]
```

- `category` can be a folder name or a category title. Matching is not case sensitive.
- If the category matches nothing, a new category is created.
- `date` can be `dd_mm_yyyy` or `yyyy-mm-dd`.
- All four fields are required, otherwise the entry is skipped with a warning.

## Mixing posts and links in one category

HTML posts, Markdown posts and external links can all share a category. They are sorted together by date. To keep a Medium article under the same heading as your own pages, put the `.url` file in that folder, or use `_links.json` with that category name.

## Category title, description and order (optional)

Add `_category.json` inside a category folder:

```json
{
  "title": "Python & Data Structures",
  "desc": "Reference guides and interactive handbooks for core programming constructs.",
  "order": 1
}
```

| Field   | Effect                                                                      |
| ------- | --------------------------------------------------------------------------- |
| `title` | Heading shown on the site. Use it for names the folder cannot hold, like `&`. |
| `desc`  | One-line description under the heading.                                     |
| `order` | Lower numbers appear first. Without it, categories with the newest post come first. |

## Hiding or removing posts

- Add `draft: true` to a Markdown post's front matter.
- Or move the file into a folder starting with `_`, such as `blog/_drafts/`.
- Or delete the file. The next run removes it from the list.

## Things to remember

- **Never edit the blog list in `index.html` by hand.** The block between `BLOG:START` and `BLOG:END` and the pre-rendered list are overwritten on every run.
- **Keep `.nojekyll` in the repo root.** Without it, GitHub Pages can skip files.
- **Run the build before pushing.** The site does not read the `blog/` folder live. It shows whatever the last run wrote into `index.html`.
- **Read the warnings.** If a post is missing from the site, the script output says why (wrong file name, bad date, missing URL).

## Troubleshooting

| Problem                          | Likely cause                                                       |
| -------------------------------- | ------------------------------------------------------------------ |
| Post missing from the list       | File name is not `dd_mm_yyyy_name.ext`, the date is invalid, or the file is in a folder starting with `_`. |
| Markdown post shows a 404        | `blog/generated/` was not pushed, or `.nojekyll` is missing.       |
| Medium link not showing          | The URL does not start with `http(s)://`, or the `_links.json` entry is missing a field. |
| Wrong title                      | Add a `title:` line (`.url`), `title:` front matter (`.md`), or a `<title>` tag (`.html`). |
| `BLOG:START markers not found`   | Use the supplied `index.html`, which contains the markers.         |
| Push asks for a password         | Set up a GitHub personal access token or SSH key for `git push`.   |
