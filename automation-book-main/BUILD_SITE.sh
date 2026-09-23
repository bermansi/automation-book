#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORD_FILE="${1:-$PROJECT_DIR/private-source/Automation_book4Aug2026.docx}"

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
python3 -m pip install -r requirements.txt
python3 scripts/build-from-word-semantic.py "$WORD_FILE" --out docs
python3 scripts/validate-book.py --docs docs

echo "BUILD AND VALIDATION SUCCEEDED"
echo "Preview: $PROJECT_DIR/docs/index.html"

