#!/usr/bin/env python3
from __future__ import annotations

import argparse
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

expected_parts = {
    "1.7.1": list("אבגדהו"),
    "1.7.2": list("אבגדהו"),
    "1.7.3": list("אבגד"),
    "1.7.5": list("אבגדהו"),
    "5.1.1": list("אבגד"),
    "5.2.1": list("אבג"),
    "5.3.1": list("אבג"),
    "5.4.1": list("אבג"),
    "5.5.1": list("אבג"),
}

for exercise in exercises:
    number = exercise.get("number")
    question = exercise.get("questionHtml", "")
    solution = exercise.get("solutionHtml", "")
    if not question.strip():
        errors.append(f"Empty question: {number}")
    if "לא זוהה פתרון" in solution:
        errors.append(f"Unidentified solution: {number}")
    check_images(question + solution, str(number))

    parts = exercise.get("parts", [])
    if number in expected_parts:
        labels = [part.get("label") for part in parts]
        if labels != expected_parts[number]:
            errors.append(f"Wrong part labels for {number}: {labels}")
    elif parts:
        labels = [part.get("label") for part in parts]
        expected_labels = [chr(ord("א") + index) for index in range(len(parts))]
        if len(parts) < 2 or labels != expected_labels:
            errors.append(f"Non-sequential grouped parts in {number}: {labels}")

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
chapter_status = {chapter.get("number"): chapter.get("status") for chapter in chapters}
if set(chapter_status) != set("12345"):
    errors.append(f"Expected chapters 1–5, found: {sorted(chapter_status)}")

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
    section_statuses = [section.get("status") for section in chapter.get("sections", [])]
    if any(status not in {"implemented", "planned"} for status in section_statuses):
        errors.append(f"Chapter {chapter.get('number')} has an invalid section status")
    expected_status = "partial" if "planned" in section_statuses else "implemented"
    if chapter.get("status") != expected_status:
        errors.append(
            f"Chapter {chapter.get('number')} status should be {expected_status}, "
            f"not {chapter.get('status')}"
        )

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
if "3.3" not in public_section_ids:
    errors.append("Planned image-processing section 3.3 is missing")
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
    for needle in ['dir="rtl"', "MathJax", "assets/book-data.js", "assets/app.js", "סעיפים 4.1–4.7", 'id="chapter-title"', 'id="content-title"']:
        if needle not in html:
            errors.append(f"Missing {needle} in docs/index.html")

app = root / "assets" / "app.js"
if not app.exists():
    errors.append("Missing docs/assets/app.js")
else:
    app_html = app.read_text(encoding="utf-8")
    for needle in ["renderExerciseBody", "exercise-part", "solutionHtml", "chapterTitle.textContent", '<h4 class="exercise-title">']:
        if needle not in app_html:
            errors.append(f"app.js is missing progressive-part support: {needle}")

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
    solution = exercise.get("solutionHtml", "")
    soup_lists = re.findall(r'<ol[^>]*class="[^"]*controller-subanswers[^"]*"[^>]*type="A"', solution)
    if "<ol" in solution and not soup_lists:
        errors.append(f"Controller solution subparts are not lettered in {exercise.get('number')}")

matrix_images = set(re.findall(r"media/(matrix-[^\"']+\.png)", raw))
for filename in matrix_images:
    path = root / "media" / filename
    if not path.exists() or path.stat().st_size < 500:
        errors.append(f"Missing or empty rasterized image-processing matrix: {filename}")

if errors:
    print("Validation failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)
print(
    f"Validation passed: {len(exercises)} public exercises, corrected Karnaugh maps, "
    "rasterized matrices, hierarchy, and publication-safety checks are complete."
)
