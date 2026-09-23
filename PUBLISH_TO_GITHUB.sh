#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="${REPO_URL:-}"
BRANCH="${BRANCH:-main}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-Update automation book from Word}"
SKIP_BUILD="${SKIP_BUILD:-0}"

if [[ ! -f "$PROJECT_DIR/private-source/.book-handoff" ]]; then
  echo "ERROR: Run this script from the extracted, complete book handoff." >&2
  echo "The GitHub checkout is missing the private source and is not the publishing folder." >&2
  exit 1
fi

if [[ -z "$REPO_URL" ]]; then
  echo "ERROR: Set REPO_URL to the exact GitHub repository URL." >&2
  echo 'Example: REPO_URL="https://github.com/OWNER/automation-book.git" bash PUBLISH_TO_GITHUB.sh' >&2
  exit 1
fi

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
  if command -v python >/dev/null 2>&1; then
    python "$PROJECT_DIR/scripts/validate-book.py" --docs "$PROJECT_DIR/docs"
  elif command -v python3 >/dev/null 2>&1; then
    python3 "$PROJECT_DIR/scripts/validate-book.py" --docs "$PROJECT_DIR/docs"
  elif command -v py >/dev/null 2>&1; then
    py -3 "$PROJECT_DIR/scripts/validate-book.py" --docs "$PROJECT_DIR/docs"
  else
    echo "ERROR: Python 3 is required to validate the public site before uploading." >&2
    exit 1
  fi
else
  "$PROJECT_DIR/BUILD_SITE.sh" "${1:-$PROJECT_DIR/private-source/Automation_book_current.docx}"
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
if command -v python >/dev/null 2>&1; then
  python scripts/validate-book.py --docs docs
elif command -v python3 >/dev/null 2>&1; then
  python3 scripts/validate-book.py --docs docs
else
  py -3 scripts/validate-book.py --docs docs
fi
git add -A
git diff --cached --check
if git diff --cached --quiet; then
  echo "No public changes to upload."
  exit 0
fi

git commit -m "$COMMIT_MESSAGE"
git push origin "$BRANCH"
echo "Upload completed: $REPO_URL ($BRANCH)"
