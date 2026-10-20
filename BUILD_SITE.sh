#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

python3 -m venv "$PROJECT_DIR/.venv"
BUILD_PYTHON="$PROJECT_DIR/.venv/bin/python3"
"$BUILD_PYTHON" -m pip install -r "$PROJECT_DIR/requirements.txt"
BUILD_TEMP="$(mktemp -d "$PROJECT_DIR/.book-build-XXXXXX")"
trap 'rm -rf -- "$BUILD_TEMP"' EXIT
cp -R "$PROJECT_DIR/docs" "$BUILD_TEMP/docs"
"$BUILD_PYTHON" "$PROJECT_DIR/scripts/build-from-word-semantic.py" "$@" --out "$BUILD_TEMP/docs"
"$BUILD_PYTHON" "$PROJECT_DIR/scripts/validate-book.py" --docs "$BUILD_TEMP/docs"
"$BUILD_PYTHON" "$PROJECT_DIR/scripts/summarize-question-changes.py" --before "$PROJECT_DIR/docs" --after "$BUILD_TEMP/docs"
mv "$PROJECT_DIR/docs" "$BUILD_TEMP/previous-docs"
mv "$BUILD_TEMP/docs" "$PROJECT_DIR/docs"

mkdir -p "$PROJECT_DIR/private-source"
printf 'Local source build validated.\n' > "$PROJECT_DIR/private-source/.book-handoff"

echo "BUILD AND VALIDATION SUCCEEDED"
echo "Preview: $PROJECT_DIR/docs/index.html"
if [[ "$(uname -s)" == "Darwin" ]]; then
  open "$PROJECT_DIR/docs/index.html"
fi
