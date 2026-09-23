# Automation and Integrated Systems Exercise Book

This project builds a Hebrew GitHub Pages exercise book from a canonical Word
document. The default private source path is:

`private-source/Automation_book4Aug2026.docx`

This complete handoff includes the current private Word source at that path, so
`BUILD_SITE_WINDOWS.bat` can be started by double-clicking it. A newer `.docx`
can instead be dragged onto the helper.

The generated, publishable website is already available in `docs/`.

The current importer discovers chapters, sections, questions, and solutions
from the Word document structure. It no longer depends on fixed Pandoc block
positions. A manager can therefore edit a question in place, add a question by
copying nearby structure, or remove a question from the public site by leaving
its styled heading as an empty draft. Every published solution uses a separate
`פתרון` paragraph.

## Quick start

On Windows, double-click `BUILD_SITE_WINDOWS.bat`. A newer Word file can also
be dragged onto that file. The helper supports edit-only, add-only,
delete-only, and mixed changes, prints a question-change summary, and only
replaces `docs/` after a staged build passes validation.

On macOS or Linux:

```bash
bash BUILD_SITE.sh
```

After checking the generated site, publish it with:

```bash
bash PUBLISH_TO_GITHUB.sh
```

On Windows, after `BUILD_SITE_WINDOWS.bat` has already ended with
`BUILD AND VALIDATION SUCCEEDED`, open Git Bash in the project folder and use:

```bash
SKIP_BUILD=1 bash PUBLISH_TO_GITHUB.sh
```

This uploads the existing, already-validated generated site without trying to
run Python, Pandoc, or LibreOffice a second time inside Git Bash.

The default repository is:

`https://github.com/EyalBriman/automation-book.git`

To use another repository:

```bash
REPO_URL="https://github.com/USER/REPOSITORY.git" bash PUBLISH_TO_GITHUB.sh
```

## Required software

- Python 3.10 or newer.
- Pandoc.
- LibreOffice Writer.
- Git for `PUBLISH_TO_GITHUB.sh`.
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
  private-source/Automation_book4Aug2026.docx --out docs
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

- The August 2026 build publishes 77 questions, including the new mean-shift
  question 3.2.3.
- The two empty question headings in section 3.3 remain drafts until they have
  complete question and solution content.
- Section 4.8 is intentionally excluded from publication.
- Duplicate exam headings in chapter 5 are published sequentially as sections
  5.1 through 5.5.
