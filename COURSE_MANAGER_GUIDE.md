# Course Manager Guide: Updating the Exercise Book

This guide is for a course manager who is not a programmer.

The short version is: **make the change in Word, rebuild the website, inspect
the result, and only then publish the generated public files.** Replacing or
uploading the Word file alone does not update the website.

There is one Windows workflow for every type of change. The helper does not
edit Word for you. It reads the Word file, rebuilds the complete website in a
safe temporary folder, reports which question numbers appear to have changed,
validates the result, and replaces `docs/` only if validation succeeds.

## Before every change

1. Start from the newest Word file and newest repository version.
2. Make a backup copy of the Word file.
3. Edit only the private Word source. Do not edit `docs/assets/book-data.js` or
   other generated website files by hand.
4. Use one Word editor at a time when possible.

The default source location is:

`private-source/Automation_book_current.docx`

If the DOCX is stored elsewhere, drag it onto `BUILD_SITE_WINDOWS.bat`.

## Inspecting this handoff

The supplied ZIP already contains a validated 79-question website and the
private Word source. Extract it into a new folder and open `docs/index.html`
to inspect the current public book before publishing. Check questions 2.2.5
and 5.6.1 and their solutions, several diagrams and tables, the RTL/LTR text,
and the sidebar title. The opening book plan should no longer be present.

The generated public question data and images are preserved from the supplied
ZIP. For future edits to Word, run `BUILD_SITE_WINDOWS.bat` and inspect its
question-change summary and browser preview before publishing a new build.

## Editing an existing question

1. Open the current Word file.
2. Find the question.
3. Edit inside the existing question block.
4. Keep the question heading at the same Word list level.
5. Keep `פתרון` or `פתרון:` in its own separate paragraph.
6. Edit the solution, images, and tables as needed.
7. Save and close Microsoft Word.
8. Run `BUILD_SITE_WINDOWS.bat`.
9. Confirm that the change summary lists the expected changed number and does
   not show an unexpected addition, removal, or renumbering warning.
10. Inspect the changed question, its solution, and the questions immediately
    before and after it.

Do not type or change the public question number as ordinary text. For normal
questions, the importer reads the Word list structure and calculates the public
number.

## Questions with subparts

Use one Word numbering system for the question parts: either Hebrew
`א, ב, ג, ...` or numeric `1, 2, 3, ...`. Apply real Word list numbering to all
question parts. This question list is authoritative: the importer uses its
scheme and its number of items for the solution. Do not use Latin `A, B, C`.

Both solution arrangements are supported:

1. **Answer after each subpart:** put the subpart content, then a separate
   `פתרון` paragraph and that subpart's answer. Repeat for every subpart. The
   website labels the parts according to the Word list: `א, ב, ג` or `1, 2, 3`.
2. **All answers at the end:** put one separate `פתרון` paragraph after all
   subparts. Separate the answers with sequential headings. The importer makes
   those headings match the question's Word list, including its Hebrew or
   numeric scheme and its exact number of parts. Use ordinary bullets for
   supporting lists inside an answer so they are not mistaken for new parts.

The validator stops publication if it cannot match the answers to the number
of Word question parts, or if it finds generated Latin labels, a mixed label
system, a late starting label, or a skipped label.

## Adding a new question

The safest method is to copy a complete question from the same section,
including its question heading, content, `פתרון` paragraph, and solution. Paste
it immediately after the last question in that section and replace its content.
Adding at the end avoids renumbering existing questions and their
question-specific diagrams.

### Chapters 1 to 3

1. Copy an entire existing question from the same section.
2. Paste it after the last question in that section.
3. Keep the question heading at the same multilevel-list level. Do not type a
   question number manually in a normal paragraph.
4. Replace the question content.
5. Keep a separate paragraph containing exactly `פתרון` or `פתרון:`.
6. Replace the solution content.
7. Save and close Word.
8. Run `BUILD_SITE_WINDOWS.bat`.
9. Confirm that the change summary lists the new public question number.

The public number is generated from the question's position. For example, the
third question in section 3.2 becomes 3.2.3.

### Chapter 4

Copy a complete question block from the same section. Keep the heading pattern
`1)`, `2)`, `3)`, and update the number according to its position. Keep
`פתרון` in a separate paragraph.

Section 4.8 is intentionally excluded. Content placed in section 4.8 will not
appear on the public website.

### Chapter 5 and multi-part questions

Copy a complete exam or part using the same Word structure. Each new part
should be a numbered Word-list paragraph followed by a separate `פתרון`
paragraph. The website assigns Hebrew or numeric part labels automatically,
according to the list format used in Word.

Several existing exams contain historical formatting exceptions that the
importer already recognizes. New questions should use the regular structure
with an explicit solution paragraph for every part.

## Deleting a question from the public website

### Safe method for the course manager

Do not physically delete a middle question heading. That would renumber later
questions in the same section and may attach an established diagram to the
wrong question.

Instead, turn the question into an empty draft:

1. Make a backup of the Word file.
2. Find the question to remove.
3. Keep only its styled question heading. Do not change its Word list level.
4. Delete the question text below the heading.
5. Delete the separate `פתרון` or `פתרון:` paragraph.
6. Delete the solution text, images, and tables belonging to that question.
7. Save and close Word.
8. Run `BUILD_SITE_WINDOWS.bat`.
9. In the change summary, confirm that the number appears under
   `Removed public numbers` and under `Draft headings`.
10. In the opened website, confirm that the question is absent and that the
    questions before and after it are still correct.

This leaves an unused heading in the private Word source. The heading keeps
later public numbers stable, but the empty draft is not published.

If the number itself must disappear and all later questions must be renumbered,
ask the technical maintainer to do that migration. Every later title, solution,
fixed image, and cross-reference in the section must then be checked.

## Draft questions

A question heading without a recognized solution paragraph is treated as a
draft and is not published. Empty draft headings can reserve a future question
number or safely remove a question without renumbering later content.

To publish a draft later, add real question content, a separate `פתרון`
paragraph, and the solution. It will be included in the next successful build.

## Images, tables, and diagrams

- For new images, use Word's **In Line with Text** wrapping option.
- Regular Word tables can be included in questions and solutions.
- A diagram made from many floating Word shapes may need to be flattened into
  one PNG image.
- If an image is missing from the generated website, do not publish. Save the
  diagram as PNG and insert it as an inline image.
- Some established Karnaugh maps and diagrams are also stored in
  `source/fixed-visuals` to guarantee stable output.

## RTL and LTR behavior

The Word file provides the text and document structure, but the website
controls directionality during the build:

- Hebrew paragraphs and tables are marked RTL.
- English text, variables, formulas, and Arduino code are isolated as LTR.
- Images receive fixed dimensions to prevent layout movement during loading.

Do not add HTML or RTL code to the Word file. After every update, check
parentheses, numbers, units, formulas, and English text in the browser.

## One-time installation on Windows

Install:

1. Python 3. During installation, select **Add Python to PATH**.
2. Pandoc.
3. LibreOffice Writer.
4. Git for Windows, which includes Git Bash.

GitHub Desktop is optional if a graphical Git workflow is preferred, but the
publishing command below is run in Git Bash.

Restart Windows after installation.

## Building on Windows

1. Close Microsoft Word.
2. Double-click `BUILD_SITE_WINDOWS.bat` to use the bundled source, or drag a
   newer DOCX file onto it.
3. Wait while the helper rebuilds the complete website.
4. Read the informational `QUESTION CHANGE SUMMARY` in the command window.
5. Wait for `BUILD AND VALIDATION SUCCEEDED`.
6. Inspect the website opened by the helper.

The helper builds in a temporary folder first. If conversion or validation
fails, the existing `docs/` website is not replaced.

The change summary compares normalized visible wording and is informational; it
does not block a valid build. The validator and browser inspection are the
authoritative checks for images, tables, Word-list numbering, and subparts.

If an error appears, do not publish. Copy the complete error message and send
it to the technical maintainer.

## Building on macOS or Linux

After installing Python 3, Pandoc, and LibreOffice, run:

```bash
bash BUILD_SITE.sh
```

To build from another Word file:

```bash
bash BUILD_SITE.sh "/full/path/to/new-version.docx"
```

The Windows change summary is provided by the BAT workflow. On macOS or Linux,
manually inspect the generated question list after building.

## Inspection checklist

Before publication, confirm that:

- The change summary is reasonable for the intended Word update.
- No unexpected renumbering warning appears. If it does, inspect every shifted
  question and contact the technical maintainer before publishing.
- The question number and title are correct.
- The question and solution were not reversed.
- All intended text, and only intended text, is public.
- Images, tables, Karnaugh maps, and diagrams appear correctly.
- Hebrew, English, numbers, and formulas appear in the correct order.
- Multi-part questions open one part at a time.
- Validation ends with `Validation passed`.
- No `.docx` file is included in the Git changes.

## Publishing

The included Bash helper can build, validate, and publish. The repository URL
must always be stated explicitly:

```bash
REPO_URL="https://github.com/CURRENT_OWNER/automation-book.git" \
  bash PUBLISH_TO_GITHUB.sh
```

On Windows, first complete the BAT build and inspect the preview. Then open Git
Bash in the project folder and upload the already-generated site with:

```bash
REPO_URL="https://github.com/CURRENT_OWNER/automation-book.git" \
  SKIP_BUILD=1 \
  COMMIT_MESSAGE="Fix Windows build and add question 2.2.5" \
  bash PUBLISH_TO_GITHUB.sh
```

Use `EyalBriman` as `CURRENT_OWNER` while the repository is still under Eyal,
or `Bermansi` after the transfer is complete.

This prebuilt upload mode validates the generated website with Python 3 and
does not require Pandoc or LibreOffice. The publishing helper also checks for
the private handoff marker, so it cannot accidentally publish from a bare
GitHub checkout or a parent folder containing a nested project.

The script excludes `private-source/` and all Word files from the public
repository.

GitHub Desktop can also be used: Fetch/Pull, run the build, verify that the
Word file is absent from the changes, Commit, and Push. There is no need to
upload a ZIP through the GitHub website.

## Receiving a new Word version

1. Keep a backup of the new DOCX file.
2. Confirm that edits, additions, and deletions follow the structures described
   above.
3. Replace `private-source/Automation_book_current.docx`, or drag the new file
   onto the Windows helper.
4. Build and validate the website.
5. Read the change summary and inspect all affected questions and section
   boundaries.
6. Publish the generated website and code, but never the Word source.

## Golden rule

Edit in place, add by copying a complete nearby block, and delete by leaving an
empty draft heading. Keep `פתרון` separate, rebuild, inspect, and only then
publish.
