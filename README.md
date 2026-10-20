# Automation and Integrated Systems Exercise Book

This project builds a Hebrew GitHub Pages exercise book from **five Word files,
one per chapter (פרק 1–5)**. Put them in `private-source/chapters/` as
`chapter-1.docx` through `chapter-5.docx`, then run `bash BUILD_SITE.sh`.
You can instead pass five quoted paths in chapter order, or use five explicit
`--chapter "NUMBER=/path/file.docx"` assignments. See [UPDATE_ON_MAC.md](UPDATE_ON_MAC.md)
for copyable commands, setup, and publishing instructions.

The supplied website in `docs/` has **85 public questions**. This archive includes all five October 2026
Word sources under `private-source/chapters/`. Rebuilding imports all current questions from
your sources; the total is not fixed. The former single combined Word input is
still supported. Word sources stay private and are excluded from publication.

The present site keeps the questions, solutions, and images from the supplied
public ZIP. Sigal's requested changes affect only the interface: the redundant
opening book plan is removed, and the sidebar is titled `תוכן העניינים`.

The current importer discovers chapters, sections, questions, and solutions
from each Word document’s structure. It no longer depends on fixed Pandoc block
positions. A manager can therefore edit a question in place, add a question by
copying nearby structure, or remove a question from the public site by leaving
its styled heading as an empty draft. Every published solution uses a separate
`פתרון` paragraph. The question's Word list is the source of truth for its
parts. A question may use Hebrew `א, ב, ג` or numeric `1, 2, 3`; the importer
uses the same scheme and the same number of labels in its solution. This works
both when every part is followed by its solution and when all answers are
collected at the end. Supporting lists inside an answer are not treated as
additional parts.

## Quick start

For macOS preview, publishing, and later Word edits, see
[UPDATE_ON_MAC.md](UPDATE_ON_MAC.md). The Mac build helper uses a private Python
environment, finds LibreOffice in `/Applications`, and validates the new site
before replacing the previous build.

To inspect the included website on Windows, open `docs/index.html` in a browser.
Check the sidebar, several questions and their solutions, and images before
publishing. This is the same local preview opened by the Windows build helper.

For a later Word edit, save the five private Word files and double-click
`BUILD_SITE_WINDOWS.bat` with the standard folder in place, or pass the five
quoted DOCX paths in chapter order from Command Prompt. The helper rebuilds
the website in a temporary folder, reports question changes, validates it,
and opens the new preview. It replaces `docs/` only after validation succeeds.
Review its change summary and preview before publishing any rebuilt version.

The change summary is informational and compares normalized visible wording.
The full validator and the opened browser preview remain the checks for images,
tables, list numbering, subparts, and page behavior.

To rebuild from Word on macOS or Linux:

```bash
bash BUILD_SITE.sh
```

After checking the included or newly generated site, publish from the extracted
handoff folder with the repository URL:

```bash
REPO_URL="https://github.com/bermansi/automation-book.git" \
  SKIP_BUILD=1 \
  bash PUBLISH_TO_GITHUB.sh
```

On Windows, open Git Bash in the extracted handoff folder after inspecting the
included site, or after a Word build ends with `BUILD AND VALIDATION SUCCEEDED`:

```bash
REPO_URL="https://github.com/bermansi/automation-book.git" \
  SKIP_BUILD=1 \
  bash PUBLISH_TO_GITHUB.sh
```

This mode validates and uploads the existing site without rebuilding from Word.
Python 3 is needed for validation; Pandoc and LibreOffice are needed only for a
Word rebuild. The publishing script refuses to run from a bare GitHub checkout,
which has no private handoff marker.

To use another repository:

```bash
REPO_URL="https://github.com/OWNER/automation-book.git" \
  SKIP_BUILD=1 \
  COMMIT_MESSAGE="Add question 2.2.5 and fix Hebrew subparts" \
  bash PUBLISH_TO_GITHUB.sh
```

## Required software

- Python 3.10 or newer.
- Pandoc.
- LibreOffice Writer.
- Git for Windows, which includes Git Bash, for `PUBLISH_TO_GITHUB.sh`.
- The Python packages listed in `requirements.txt`.

The build helpers install or check the Python packages automatically.

## Generated files

- `docs/` contains the complete public website.
- `docs/assets/book-data.js` contains the generated book structure, questions,
  and solutions.
- `docs/media/` contains only images referenced by the public website.

The browser does not read the Word file directly. Every Word change requires a
new build and validation run.

The website controls text direction: Hebrew paragraphs use RTL, while English,
mathematical expressions, variables, and Arduino code are isolated as LTR.

## Manual build commands

```bash
python3 -m pip install -r requirements.txt
python3 scripts/build-from-word-semantic.py \
  private-source/chapters --out docs
python3 scripts/validate-book.py --docs docs
```

## Privacy and publication safety

All `.docx` files and the complete `private-source/` directory are ignored by
Git. The publishing script also explicitly excludes Word files and the private
source directory.

The supplied five Word sources are private. They are ignored by Git and
excluded by the publishing script. The auxiliary `thelink.docx` is kept in
`private-source/` and is not processed as a chapter.

See [COURSE_MANAGER_GUIDE.md](COURSE_MANAGER_GUIDE.md) for the complete editing,
building, checking, and publication procedure.

## Current publication rules

- The included public website contains 85
  questions, including questions 2.2.5 and 5.6.1 and the mean-shift question
  3.2.3.
- Question 3.2.2 contains the corrected K-means initialization from the 2026
  exam solution.
- Empty sections are omitted; a formerly empty section may be published when
  complete questions are added to its Word source.
- The website shows only chapters and sections containing published questions;
  it does not display completion-status badges.
- Section 4.8 is intentionally excluded from publication.
- Exam headings in chapter 5 are published sequentially as sections 5.1
  onward; new complete exams are discovered from the same structure.

## Importer checks

```bash
python3 -m unittest discover -s tests -v
```

These generate representative Word fixtures, test five-file mapping and image
collisions, and compare a real Pandoc conversion of split and combined inputs.
Pandoc and LibreOffice are required for the conversion check. The actual five
course Word files must still be checked after import.
