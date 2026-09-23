# Automation and Integrated Systems Exercise Book

This project builds a Hebrew GitHub Pages exercise book from a canonical Word
document. The default private source path is:

`private-source/Automation_book_current.docx`

This complete handoff includes the private Word source at that path and the
validated 79-question generated website in `docs/`. The Word source is private:
the publishing script excludes it from the public repository.

The present site keeps the questions, solutions, and images from the supplied
public ZIP. Sigal's requested changes affect only the interface: the redundant
opening book plan is removed, and the sidebar is titled `תוכן העניינים`.

The current importer discovers chapters, sections, questions, and solutions
from the Word document structure. It no longer depends on fixed Pandoc block
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

To inspect the included website on Windows, open `docs/index.html` in a browser.
Check the sidebar, several questions and their solutions, and images before
publishing. This is the same local preview opened by the Windows build helper.

For a later Word edit, save the private Word file and double-click
`BUILD_SITE_WINDOWS.bat`, or drag another `.docx` onto it. The helper rebuilds
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
  private-source/Automation_book_current.docx --out docs
python3 scripts/validate-book.py --docs docs
```

## Privacy and publication safety

All `.docx` files and the complete `private-source/` directory are ignored by
Git. The publishing script also explicitly excludes Word files and the private
source directory.

The Word source is included in this handoff ZIP for local course management.
It is ignored by Git and excluded by the publishing script, so it is not
uploaded to the public GitHub repository.

See [COURSE_MANAGER_GUIDE.md](COURSE_MANAGER_GUIDE.md) for the complete editing,
building, checking, and publication procedure.

## Current publication rules

- The included September 2026 public website contains 79
  questions, including questions 2.2.5 and 5.6.1 and the mean-shift question
  3.2.3.
- Question 3.2.2 contains the corrected K-means initialization from the 2026
  exam solution.
- Empty section 3.3 (מאפיינים) has been removed from Word and from the website.
- The website shows only chapters and sections containing published questions;
  it does not display completion-status badges.
- Section 4.8 is intentionally excluded from publication.
- Exam headings in chapter 5 are published sequentially as sections 5.1
  through 5.6.
