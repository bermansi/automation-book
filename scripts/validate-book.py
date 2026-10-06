#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html as html_module
import hashlib
import json
import re
import sys
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--docs", type=Path, default=Path("docs"))
args = parser.parse_args()
root = args.docs
errors: list[str] = []


def check_images(html: str, label: str) -> None:
    for image_tag in re.findall(r"<img\b[^>]*>", html):
        src_match = re.search(r'src="([^"]+)"', image_tag)
        if not src_match:
            errors.append(f"Image without src in {label}")
            continue
        src = src_match.group(1)
        path = root / src
        if not path.exists():
            errors.append(f"Missing image {src} in {label}")
        elif path.stat().st_size < 500:
            errors.append(f"Suspiciously small image {src} in {label}")
        for required_attr in ['width="', 'height="', 'loading="eager"', 'decoding="sync"']:
            if required_attr not in image_tag:
                errors.append(f"Unstable image layout for {src} in {label}: missing {required_attr}")


def explicit_solution_labels(fragment: str) -> tuple[str | None, list[str]]:
    """Read explicit top-level answer labels such as א. or 1. from paragraphs."""
    hebrew: list[str] = []
    numeric: list[str] = []
    for paragraph in re.findall(r"<p\b[^>]*>(.*?)</p>", fragment, flags=re.DOTALL | re.IGNORECASE):
        text = html_module.unescape(re.sub(r"<[^>]+>", "", paragraph))
        text = re.sub(r"\s+", " ", text).strip()
        hebrew_match = re.match(r"^([א-ת])[.)]\s*", text)
        numeric_match = re.match(r"^(\d+)[.)]\s*", text)
        if hebrew_match:
            hebrew.append(hebrew_match.group(1))
        elif numeric_match:
            numeric.append(numeric_match.group(1))
    if hebrew and numeric:
        return "mixed", hebrew + numeric
    if hebrew:
        return "hebrew", hebrew
    if numeric:
        return "numeric", numeric
    return None, []


def check_solution_label_sequence(fragment: str, number: str) -> None:
    scheme, labels = explicit_solution_labels(fragment)
    if scheme == "mixed":
        errors.append(f"Mixed Hebrew and numeric answer labels in {number}: {labels}")
        return
    if len(labels) < 2:
        return
    if scheme == "hebrew":
        expected = [chr(ord("א") + index) for index in range(len(labels))]
    else:
        expected = [str(index) for index in range(1, len(labels) + 1)]
    if labels != expected:
        errors.append(f"Answer labels in {number} must start at the first part and be sequential: {labels}")


js_path = root / "assets" / "book-data.js"
if not js_path.exists():
    errors.append("Missing docs/assets/book-data.js")
    data = {"exercises": [], "chapters": []}
    raw = ""
else:
    raw = js_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw.removeprefix("window.BOOK_DATA = ").rstrip(" ;\n"))
    except Exception as exc:
        errors.append(f"Could not parse book-data.js: {exc}")
        data = {"exercises": [], "chapters": []}

exercises = data.get("exercises", [])
actual_numbers = [exercise.get("number") for exercise in exercises]
actual = set(actual_numbers)
if None in actual or "" in actual:
    errors.append("An exercise is missing its public number")
if len(actual_numbers) != len(actual):
    errors.append("Exercise numbers are not unique")

structure = data.get("structure", {})
if structure.get("publishedQuestions") != len(exercises):
    errors.append(
        "Published-question metadata does not match the generated exercises: "
        f"{structure.get('publishedQuestions')} != {len(exercises)}"
    )
drafts = set(structure.get("draftQuestions", []))
if drafts & actual:
    errors.append("Draft question headings were published: " + ", ".join(sorted(drafts & actual)))

ids = [exercise.get("id") for exercise in exercises]
if len(ids) != len(set(ids)):
    errors.append("Exercise IDs are not unique")

expected_part_counts = {
    "1.7.1": 6,
    "1.7.2": 6,
    "1.7.3": 4,
    "1.7.5": 6,
    "5.1.1": 4,
    "5.2.1": 3,
    "5.3.1": 3,
    "5.4.1": 3,
    "5.5.1": 3,
    "5.6.1": 3,
}

for exercise in exercises:
    number = exercise.get("number")
    question = exercise.get("questionHtml", "")
    solution = exercise.get("solutionHtml", "")
    combined_html = question + solution
    if 'type="A"' in combined_html or "controller-subanswers" in combined_html:
        errors.append(f"Latin answer labels were generated in {number}; follow the Word numbering instead")
    if not question.strip():
        errors.append(f"Empty question: {number}")
    if "לא זוהה פתרון" in solution:
        errors.append(f"Unidentified solution: {number}")
    check_images(question + solution, str(number))

    parts = exercise.get("parts", [])
    if parts:
        labels = [part.get("label") for part in parts]
        if labels and all(isinstance(label, str) and label.isdigit() for label in labels):
            expected_labels = [str(index) for index in range(1, len(parts) + 1)]
        elif labels and all(isinstance(label, str) and re.fullmatch(r"[א-ת]", label) for label in labels):
            expected_labels = [chr(ord("א") + index) for index in range(len(parts))]
        else:
            expected_labels = []
        if len(parts) < 2 or labels != expected_labels:
            errors.append(f"Non-sequential grouped parts in {number}: {labels}")
        if number in expected_part_counts and len(parts) != expected_part_counts[number]:
            errors.append(
                f"Wrong number of grouped parts for {number}: {len(parts)}; "
                f"expected {expected_part_counts[number]} from the established Word structure"
            )
    elif number in expected_part_counts:
        errors.append(f"Grouped question {number} lost its part structure")

    if parts:
        for part in parts:
            label = f"{number} סעיף {part.get('label')}"
            part_question = part.get("questionHtml", "")
            part_solution = part.get("solutionHtml", "")
            if not part_question.strip():
                errors.append(f"Empty part question: {label}")
            if not part_solution.strip():
                errors.append(f"Empty part solution: {label}")
            if "לא זוהה פתרון" in part_solution:
                errors.append(f"Unidentified part solution: {label}")
            check_images(part_question + part_solution, label)
    elif not solution.strip():
        errors.append(f"Empty solution: {number}")
    else:
        check_solution_label_sequence(solution, str(number))

    source_part_labels = exercise.get("partLabels", [])
    source_part_scheme = exercise.get("partLabelScheme")
    solution_layout = exercise.get("solutionPartLayout")
    if source_part_labels:
        if source_part_scheme == "hebrew":
            expected_source_labels = [chr(ord("א") + index) for index in range(len(source_part_labels))]
        elif source_part_scheme == "numeric":
            expected_source_labels = [str(index) for index in range(1, len(source_part_labels) + 1)]
        else:
            expected_source_labels = []
        if source_part_labels != expected_source_labels:
            errors.append(f"Invalid Word-derived part labels in {number}: {source_part_labels}")
        if solution_layout == "explicit":
            solution_scheme, solution_labels = explicit_solution_labels(solution)
            if solution_scheme != source_part_scheme or solution_labels != source_part_labels:
                errors.append(
                    f"Solution labels in {number} do not match its Word question list: "
                    f"question={source_part_labels}, solution={solution_labels}"
                )
        elif solution_layout != "word-list":
            errors.append(f"Unknown solution-part layout in {number}: {solution_layout}")

    if number == "2.2.5":
        if "word-list-hebrew" not in question:
            errors.append("Question 2.2.5 must preserve its Hebrew א, ב, ג, ד list from Word")
        if len(re.findall(r"<li(?:\s|>)", question)) != 4:
            errors.append("Question 2.2.5 must contain exactly four Hebrew parts")
        if "word-list-hebrew" in solution:
            errors.append(
                "Question 2.2.5 solution condition lists must be bullets, not a second Hebrew א, ב, ג list"
            )

source_notes = [exercise.get("number") for exercise in exercises if "source-note" in exercise.get("solutionHtml", "")]
if source_notes:
    errors.append(f"Unexpected missing-source solution notes: {source_notes}")

irrigation = next((exercise for exercise in exercises if exercise.get("number") == "2.1.1"), None)
if irrigation is not None:
    irrigation_solution = irrigation.get("solutionHtml", "")
    for needle in ["תנאים להתחלת מחזור ההשקיה", "טבלת אמת עבור", "מפת קרנו עבור", "word-fixed-2-1-1-karnaugh.png"]:
        if needle not in irrigation_solution:
            errors.append(f"2.1.1 solution is missing: {needle}")

required_visual_targets = {
    "word-visual-1-1-3-solution.png": ("1.1.3", None),
    "word-visual-1-7-1-d.png": ("1.7.1", "ד"),
    "word-visual-1-7-2-d.png": ("1.7.2", "ד"),
    "word-visual-1-7-3-b.png": ("1.7.3", "ב"),
    "word-visual-1-7-4.png": ("1.7.4", None),
    "word-visual-1-7-5-c.png": ("1.7.5", "ג"),
    "word-fixed-2-1-1-karnaugh.png": ("2.1.1", None),
    "word-fixed-2-1-2-karnaugh.png": ("2.1.2", None),
    "word-fixed-2-2-1-fill-karnaugh.png": ("2.2.1", None),
    "word-fixed-2-2-1-drain-karnaugh.png": ("2.2.1", None),
    "word-fixed-2-2-1-light-karnaugh.png": ("2.2.1", None),
    "word-fixed-2-2-2-karnaugh.png": ("2.2.2", None),
    "word-fixed-2-2-3-karnaugh.png": ("2.2.3", None),
    "word-visual-5-2-a.png": ("5.2.1", "א"),
    "word-fixed-5-2-c.png": ("5.2.1", "ג"),
    "word-visual-5-3-c.png": ("5.3.1", "ג"),
    "word-fixed-5-5-button.png": ("5.5.1", "ג"),
    "word-fixed-5-5-circuit.png": ("5.5.1", "ג"),
}
exercise_by_number = {exercise.get("number"): exercise for exercise in exercises}
for filename, (question_number, part_label) in required_visual_targets.items():
    exercise = exercise_by_number.get(question_number)
    target_is_public = exercise is not None
    if target_is_public and part_label is not None:
        target_is_public = any(
            part.get("label") == part_label for part in exercise.get("parts", [])
        )
    if not target_is_public:
        continue
    path = root / "media" / filename
    if not path.exists() or path.stat().st_size < 1000:
        errors.append(f"Missing or empty generated Word visual: {filename}")
    if filename not in raw:
        errors.append(f"Generated Word visual is not referenced: {filename}")

fixed_visuals = Path(__file__).resolve().parent.parent / "source" / "fixed-visuals"
for source_visual in sorted(fixed_visuals.glob("*.png")):
    published_visual = root / "media" / source_visual.name
    if not published_visual.exists():
        # A fixed visual is not copied when its question is intentionally a
        # draft.  Active targets are checked above.
        continue
    source_hash = hashlib.sha256(source_visual.read_bytes()).hexdigest()
    published_hash = hashlib.sha256(published_visual.read_bytes()).hexdigest()
    if source_hash != published_hash:
        errors.append(f"Fixed visual changed during publication: {source_visual.name}")

for legacy in ["1-7-1d-closed-loop.png", "1-1-3-kcl-circuit.png"]:
    if legacy in raw:
        errors.append(f"Legacy manual crop is still referenced: {legacy}")

if not str(data.get("source", "")).startswith("private Word source"):
    errors.append(f"Wrong source metadata: {data.get('source')}")
if "word-drawings" not in data.get("build", ""):
    errors.append("Build metadata does not identify the Word-drawing renderer")

chapters = data.get("chapters", [])
chapter_numbers = {chapter.get("number") for chapter in chapters}
if chapter_numbers != set("12345"):
    errors.append(f"Expected chapters 1–5, found: {sorted(chapter_numbers)}")

known_sections = {
    section.get("id")
    for chapter in chapters
    for section in chapter.get("sections", [])
}
for exercise in exercises:
    if exercise.get("section") not in known_sections:
        errors.append(
            f"Exercise {exercise.get('number')} refers to unknown section {exercise.get('section')}"
        )

for chapter in chapters:
    if "status" in chapter:
        errors.append(f"Chapter {chapter.get('number')} still exposes a completion status")
    for section in chapter.get("sections", []):
        if "status" in section or "comingSoon" in section:
            errors.append(f"Section {section.get('id')} still exposes an unfinished status")

if raw.count("word-code") < 5:
    errors.append("Arduino code blocks were not consistently marked LTR")

unpublished_section = "4." + str(8)
public_section_ids = {
    section.get("id")
    for chapter in data.get("chapters", [])
    for section in chapter.get("sections", [])
}
public_exercise_sections = {exercise.get("section") for exercise in exercises}
public_exercise_numbers = {exercise.get("number") for exercise in exercises}
if {"2.3", "3.4"} & public_section_ids:
    errors.append("Unplanned review sections 2.3 or 3.4 are still present")
if "3.3" in public_section_ids:
    errors.append("Empty image-processing section 3.3 is still public")
empty_public_sections = sorted(public_section_ids - public_exercise_sections)
if empty_public_sections:
    errors.append("Public sections without questions: " + ", ".join(empty_public_sections))
if (
    unpublished_section in public_section_ids
    or unpublished_section in public_exercise_sections
    or any(str(number).startswith(unpublished_section + ".") for number in public_exercise_numbers)
):
    errors.append("Unpublished exam material is present in public book data")

referenced_media = set(re.findall(r"media/([^\"'\\]+)", raw))
actual_media = {path.name for path in (root / "media").iterdir() if path.is_file()}
unreferenced_media = sorted(actual_media - referenced_media)
if unreferenced_media:
    errors.append("Unreferenced media files are public: " + ", ".join(unreferenced_media))

index = root / "index.html"
if not index.exists():
    errors.append("Missing docs/index.html")
else:
    html = index.read_text(encoding="utf-8")
    for needle in ['dir="rtl"', "MathJax", "assets/book-data.js", "assets/app.js", '<div class="brand-title">תוכן העניינים</div>', 'תרגילים בקורס אוטומציה ומערכות משולבות', 'id="chapter-title"', 'id="content-title"']:
        if needle not in html:
            errors.append(f"Missing {needle} in docs/index.html")
    if 'id="landing"' in html or 'id="plan-grid"' in html:
        errors.append("The redundant opening book plan is still present in docs/index.html")

app = root / "assets" / "app.js"
if not app.exists():
    errors.append("Missing docs/assets/app.js")
else:
    app_html = app.read_text(encoding="utf-8")
    for needle in ["renderExerciseBody", "exercise-part", "solutionHtml", "chapterTitle.textContent", '<h4 class="exercise-title">']:
        if needle not in app_html:
            errors.append(f"app.js is missing progressive-part support: {needle}")
    for forbidden in ["ממומש", "חלקי", "בעבודה", "comingSoon", "implementedSections"]:
        if forbidden in app_html:
            errors.append(f"app.js still contains an unfinished-status marker: {forbidden}")

css = root / "assets" / "styles.css"
if not css.exists():
    errors.append("Missing docs/assets/styles.css")
else:
    css_text = css.read_text(encoding="utf-8")
    for needle in [".formula-line", ".word-code", ".word-diagram", ".source-note"]:
        if needle not in css_text:
            errors.append(f"CSS is missing {needle}")
    for needle in [
        "background: #fff !important;",
        "color-scheme: light;",
        "background: transparent !important;",
    ]:
        if needle not in css_text:
            errors.append(f"CSS is missing enforced light figure/code styling: {needle}")

chapter_2_2 = [exercise for exercise in exercises if exercise.get("section") == "2.2"]
for exercise in chapter_2_2:
    question = exercise.get("questionHtml", "")
    if "<ol" in question and "word-list-hebrew" not in question and "word-code" not in question:
        errors.append(
            f"Controller question subparts do not preserve their Word numbering in {exercise.get('number')}"
        )

matrix_images = set(re.findall(r"media/(matrix-[^\"']+\.png)", raw))
for filename in matrix_images:
    path = root / "media" / filename
    if not path.exists() or path.stat().st_size < 500:
        errors.append(f"Missing or empty rasterized image-processing matrix: {filename}")

math_array_count = 0
for exercise in exercises:
    fragments = [exercise.get("questionHtml", ""), exercise.get("solutionHtml", "")]
    for part in exercise.get("parts", []):
        fragments.extend([part.get("questionHtml", ""), part.get("solutionHtml", "")])
    for fragment in fragments:
        visible_html = html_module.unescape(fragment)
        for environment, contents in re.findall(
            r"\\begin\{(bmatrix|pmatrix|matrix|vmatrix|Vmatrix|Bmatrix|smallmatrix)\}(.*?)\\end\{\1\}",
            visible_html, re.DOTALL,
        ):
            math_array_count += 1
            rows = [row.strip() for row in re.split(r"\\\\", contents) if row.strip()]
            columns = [len(re.split(r"(?<!\\)&", row)) for row in rows]
            if not rows or len(set(columns)) != 1:
                errors.append(f"Inconsistent matrix/vector rows in {exercise.get('number')}")
        # Word arrays must be real equation matrices. Space-separated values
        # inside ordinary brackets lose the distinction between rows/columns.
        for array in re.findall(r"\\lbrack(.*?)\\rbrack", fragment, re.DOTALL):
            entries = re.sub(r"\\\s|\s+", " ", array).strip()
            if re.fullmatch(r"[+\-]?\s*\d+(?:\.\d+)?(?:\s+[+\-]?\s*\d+(?:\.\d+)?)+", entries):
                message = f"Flattened numeric matrix/vector in {exercise.get('number')}"
                if message not in errors:
                    errors.append(message)
        for paragraph in re.findall(r"<p\b[^>]*>(.*?)</p>", visible_html, re.DOTALL):
            if 'class="math"' in paragraph or 'class="display math"' in paragraph:
                continue
            text = re.sub(r"<[^>]+>", "", paragraph).strip()
            if re.match(r"^\.\s*(?:\d+|[א-ת])(?:\s|$)", text):
                errors.append(f"Reversed paragraph label in {exercise.get('number')}")

if app.exists():
    for needle in ["fixNumberLabels(list)", "number-marker", "numeric-label", "book-number"]:
        if needle not in app_html:
            errors.append(f"Missing bidirectional number-label handling in app.js: {needle}")
if css.exists():
    for needle in [".word-list-numeric", ".number-marker", "unicode-bidi: isolate;"]:
        if needle not in css_text:
            errors.append(f"Missing bidirectional number-label styling: {needle}")

if errors:
    print("Validation failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)
print(
    f"Validation passed: {len(exercises)} public exercises, corrected Karnaugh maps, "
    f"rasterized matrices, {math_array_count} equation arrays, hierarchy, "
    "number labels, and publication-safety checks are complete."
)
