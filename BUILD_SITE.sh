#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORD_FILE="${1:-$PROJECT_DIR/private-source/Automation_book_current.docx}"

# LibreOffice's macOS installer does not put soffice on the shell PATH.
if [[ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ]]; then
  export PATH="/Applications/LibreOffice.app/Contents/MacOS:$PATH"
fi

for command_name in python3 pandoc; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: $command_name is required but was not found." >&2
    exit 1
  fi
done

if ! command -v soffice >/dev/null 2>&1 && ! command -v libreoffice >/dev/null 2>&1; then
  echo "ERROR: LibreOffice Writer is required but was not found." >&2
  exit 1
fi

if [[ ! -f "$WORD_FILE" ]]; then
  echo "ERROR: Word source not found: $WORD_FILE" >&2
  exit 1
fi

cd "$PROJECT_DIR"
python3 -m venv "$PROJECT_DIR/.venv"
BUILD_PYTHON="$PROJECT_DIR/.venv/bin/python3"
"$BUILD_PYTHON" -m pip install -r requirements.txt
BUILD_TEMP="$(mktemp -d "$PROJECT_DIR/.book-build-XXXXXX")"
trap 'rm -rf -- "$BUILD_TEMP"' EXIT
cp -R docs "$BUILD_TEMP/docs"
"$BUILD_PYTHON" scripts/build-from-word-semantic.py "$WORD_FILE" --out "$BUILD_TEMP/docs"
"$BUILD_PYTHON" scripts/validate-book.py --docs "$BUILD_TEMP/docs"
"$BUILD_PYTHON" scripts/summarize-question-changes.py --before docs --after "$BUILD_TEMP/docs"
mv docs "$BUILD_TEMP/previous-docs"
mv "$BUILD_TEMP/docs" docs

echo "BUILD AND VALIDATION SUCCEEDED"
echo "Preview: $PROJECT_DIR/docs/index.html"
if [[ "$(uname -s)" == "Darwin" ]]; then
  open "$PROJECT_DIR/docs/index.html"
fi
