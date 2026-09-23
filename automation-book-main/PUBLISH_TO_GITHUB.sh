#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="${REPO_URL:-https://github.com/EyalBriman/automation-book.git}"
BRANCH="${BRANCH:-main}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-Update automation book from Word}"
SKIP_BUILD="${SKIP_BUILD:-0}"

for command_name in git tar; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: $command_name is required but was not found." >&2
    exit 1
  fi
done

if [[ "$SKIP_BUILD" == "1" ]]; then
  if [[ ! -f "$PROJECT_DIR/docs/index.html" || \
        ! -f "$PROJECT_DIR/docs/assets/book-data.js" ]]; then
    echo "ERROR: The prebuilt website is incomplete." >&2
    echo "Expected docs/index.html and docs/assets/book-data.js." >&2
    exit 1
  fi
  echo "Using the prebuilt, already-validated website in docs/."
  echo "Python, Pandoc, and LibreOffice are not required for this upload."
else
  "$PROJECT_DIR/BUILD_SITE.sh" "${1:-$PROJECT_DIR/private-source/Automation_book4Aug2026.docx}"
fi

UPLOAD_TEMP="$(mktemp -d "${TMPDIR:-/tmp}/automation-book-upload-XXXXXX")"
cleanup() {
  rm -rf -- "$UPLOAD_TEMP"
}
trap cleanup EXIT

git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$UPLOAD_TEMP/repository"

cd "$UPLOAD_TEMP/repository"
git rm -r --ignore-unmatch . >/dev/null

(
  cd "$PROJECT_DIR"
  tar \
    --exclude='./.git' \
    --exclude='./private-source' \
    --exclude='*.docx' \
    --exclude='~$*.docx' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -cf - .
) | tar -xf - -C "$UPLOAD_TEMP/repository"

cd "$UPLOAD_TEMP/repository"
git add -A
if git diff --cached --quiet; then
  echo "No public changes to upload."
  exit 0
fi

git commit -m "$COMMIT_MESSAGE"
git push origin "$BRANCH"
echo "Upload completed: $REPO_URL ($BRANCH)"
