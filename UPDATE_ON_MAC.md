# Updating the book on Mac — five Word files

There is one Word file per chapter (פרק), numbered 1–5. The website still uses
פרק / סעיף / תת־סעיף and the same public question numbering, solutions, images,
and Hebrew/math direction handling. All five sources are rebuilt together.
The supplied website was rebuilt and validated from the five October 2026
Word files and has **85 public questions**. All five files are already in
`private-source/chapters/`. The auxiliary `thelink.docx` is preserved under
`private-source/` and is not used as a chapter input.

## 1. Preview and publish this ZIP

Download `automation-book-rise-time-fixed.zip` to Downloads and run:

```bash
cd "$HOME/Downloads"
unzip automation-book-rise-time-fixed.zip -d automation-book-rise-time-fixed
cd automation-book-rise-time-fixed/automation-book-main
open docs/index.html
```

After checking the preview, run from the same folder:

```bash
REPO_URL="https://github.com/bermansi/automation-book.git" \
SKIP_BUILD=1 \
COMMIT_MESSAGE="Update automation book from five private Word sources" \
bash PUBLISH_TO_GITHUB.sh
```

This validates and uploads the already rebuilt website and the project code.
All Word files and the complete private source folder are excluded from GitHub.
Wait for the GitHub Pages workflow to succeed before checking the live site.

The chapter files are already mapped as follows. The private documents were corrected for direction, answer labels,
and question-level headings; their filenames were standardized:

| Original filename | Private build input | Destination |
| --- | --- | --- |
| `Automation_chapter1_Oct2026.docx` | `private-source/chapters/chapter-1.docx` | פרק 1 |
| `Automation_chapter2_Oct2026.docx` | `private-source/chapters/chapter-2.docx` | פרק 2 |
| `Automation_chapter3_Oct2026.docx` | `private-source/chapters/chapter-3.docx` | פרק 3 |
| `Automation_chpter4_Oct2026.docx` | `private-source/chapters/chapter-4.docx` | פרק 4 |
| `Automation_chapter5_Oct2026.docx` | `private-source/chapters/chapter-5.docx` | פרק 5 |

For later edits, update the relevant private file and leave the other four in
place. Preserve Word list levels and the question numbers. The importer reads
the current chapter 4 titles and explicit numbers, and retains the established
special controller IDs in chapter 1. The private Word sources now contain the direction, answer-label, and native
state-space matrix corrections. Question and part descriptions are not used as
extra website headings. Only chapter/section topic headings are displayed;
questions and their parts retain their numbers/letters.

## 2. Build and preview

Install these tools once if missing:

```bash
brew install pandoc
brew install --cask libreoffice
```

Save and close the Word files, then run:

```bash
cd "$HOME/Downloads/automation-book-rise-time-fixed/automation-book-main"
bash BUILD_SITE.sh
```

The script installs Python dependencies in `.venv`, builds in a temporary
folder, validates, reports added/removed/changed questions, and opens the preview.
`docs/` is replaced only after the build and validation pass. Every run uses all
five files, including when you edited only one. Inspect the change summary,
new questions, numbering, solutions, diagrams, and mixed Hebrew/math text.

## Alternative: pass all five files together

Filenames may be anything, including Hebrew and spaces. Quote each full path.
The argument order determines the destination: chapter 1, then 2, 3, 4, 5.
For example (replace these example filenames with your actual filenames):

```bash
bash BUILD_SITE.sh \
  "$HOME/Downloads/Part 1.docx" \
  "$HOME/Downloads/Part 2.docx" \
  "$HOME/Downloads/Part 3.docx" \
  "$HOME/Downloads/Part 4.docx" \
  "$HOME/Downloads/Part 5.docx"
```

Alternatively use explicit mapping; the order of these assignments is irrelevant:

```bash
bash BUILD_SITE.sh \
  --chapter "1=$HOME/Downloads/Part 1.docx" \
  --chapter "2=$HOME/Downloads/Part 2.docx" \
  --chapter "3=$HOME/Downloads/Part 3.docx" \
  --chapter "4=$HOME/Downloads/Part 4.docx" \
  --chapter "5=$HOME/Downloads/Part 5.docx"
```

You may also pass a folder containing `chapter-1.docx` through `chapter-5.docx`:

```bash
bash BUILD_SITE.sh "$HOME/Downloads/my-chapters"
```

Missing inputs, duplicate assignments, repeated input files, mismatched chapter
headings, and chapters without published questions stop the split build. Word
files are converted separately so their numbering definitions and images cannot
overwrite those in another file. Existing fixed diagram assets are still used.

## 3. Publish after checking the preview

Run from the extracted project folder:

```bash
REPO_URL="https://github.com/bermansi/automation-book.git" \
SKIP_BUILD=1 \
COMMIT_MESSAGE="Update book using five chapter Word files" \
bash PUBLISH_TO_GITHUB.sh
```

This publishes the generated website and code together. The private sources,
all DOCX files, `.venv`, and temporary build folders are excluded. The script
creates the private handoff marker after a successful local build. The GitHub
Pages workflow must succeed before the live site updates.

For a build-and-publish run, omit `SKIP_BUILD=1`; the same five inputs or
`--chapter` assignments can follow `PUBLISH_TO_GITHUB.sh`. Always preview a
build before choosing to publish it.

## Later edits and new questions

Edit the relevant chapter's Word file, preserve the existing question/list
hierarchy, and use a separate `פתרון` paragraph for each solution. Copy a nearby
question's structure for new questions. Rebuild the complete book with the same
command. There is no fixed total question count. Existing special numbering and
fixed figures remain tied to their established question IDs, so keep existing
IDs stable. For a new floating-shape diagram, insert a flattened image in Word;
new shape drawings do not automatically acquire a fixed-figure override.
Section 4.8 remains excluded from publication.

The previous single-source command remains supported:

```bash
bash BUILD_SITE.sh "/full/path/to/combined-book.docx"
```

With no arguments, the chapter folder takes precedence if it exists. If it does
not exist, the importer falls back to the old path
`private-source/Automation_book_current.docx`. An incomplete chapter folder
causes an error; it does not silently use an older combined file.
