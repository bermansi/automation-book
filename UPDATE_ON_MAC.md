# Updating the book on Mac

The corrected private Word source is `private-source/Automation_book_current.docx`.
The complete website is already built in `docs/`. Hebrew headings and subpart
labels follow right-to-left direction. English terms, code, and equations retain
their left-to-right order. The importer accepts both `1.` and `1)` headings.

## Preview and publish this ZIP

Save `automation-book-rtl-mac.zip` in Downloads. Run in Terminal:

```bash
cd "$HOME/Downloads" &&
unzip automation-book-rtl-mac.zip &&
cd automation-book-rtl-mac &&
python3 scripts/validate-book.py --docs docs &&
open docs/index.html
```

Inspect the headings, question subparts, and solutions. Then publish:

```bash
REPO_URL="https://github.com/bermansi/automation-book.git" \
SKIP_BUILD=1 \
COMMIT_MESSAGE="Fix Hebrew RTL headings and question subparts" \
bash PUBLISH_TO_GITHUB.sh
```

The publishing script validates before pushing and excludes the private Word
source, the Python environment, and temporary build folders. Wait for the
GitHub Pages workflow to succeed before checking the live site.

## After later Word edits

Install build tools once if missing:

```bash
brew install pandoc
brew install --cask libreoffice
```

Edit the private Word source, keeping question structure, numbering, and the
separate `פתרון` paragraphs. Close Word, then run from the project folder:

```bash
bash BUILD_SITE.sh
```

The script installs Python dependencies into a local virtual environment,
builds into a temporary folder, validates, reports question changes, and opens
the preview. It replaces `docs/` only after the build and validation pass.
Questions can be added or removed following `COURSE_MANAGER_GUIDE.md`;
the total count is computed from the source.

After inspecting the new preview, use the same publishing command above.
The Windows BAT helper is also retained in this handoff.
