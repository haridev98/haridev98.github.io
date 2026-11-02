#!/usr/bin/env bash
# publish.sh - rebuild the blog list and push everything to GitHub.
#
# Usage:
#   ./publish.sh                       # commit message: "Update blog (dd-mm-yyyy HH:MM)"
#   ./publish.sh "Add RAG article"     # custom commit message
#
# Put this file next to index.html and build_blog.py (the repo root).

set -euo pipefail

# always work from the folder this script lives in
cd "$(dirname "${BASH_SOURCE[0]}")"

# pick a Python interpreter
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "Python not found. Install Python 3.9+ first." >&2; exit 1
fi

# make sure we are inside a git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "This folder is not a git repository." >&2; exit 1; }

# keep GitHub Pages (Jekyll) from skipping any files
[ -f .nojekyll ] || touch .nojekyll

echo "==> Building blog..."
"$PY" build_blog.py

MSG="${1:-Update blog ($(date '+%d-%m-%Y %H:%M'))}"

echo "==> Committing..."
git add -A
if git diff --cached --quiet; then
  echo "Nothing changed, nothing to push."
  exit 0
fi
git commit -m "$MSG"

echo "==> Pushing..."
if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
  git push
else
  git push -u origin HEAD   # first push of this branch
fi

echo "Done. GitHub Pages will update in a minute or two."
