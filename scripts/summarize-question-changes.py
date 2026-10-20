#!/usr/bin/env python3
"""Print a manager-friendly summary of changes between two generated books."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path


def load_book(path: Path) -> dict:
    if path.is_dir():
        path = path / "assets" / "book-data.js"
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw.removeprefix("window.BOOK_DATA = ").rstrip(" ;\n"))


def text_only(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def question_fingerprint(exercise: dict) -> str:
    pieces = [text_only(exercise.get("questionHtml", ""))]
    for part in exercise.get("parts", []):
        pieces.append(text_only(part.get("questionHtml", "")))
    return hashlib.sha256("\n".join(pieces).encode("utf-8")).hexdigest()


def visible_content_fingerprint(exercise: dict) -> str:
    """Compare visible wording, not platform-dependent generated HTML."""
    comparable = {
        "title": text_only(str(exercise.get("title", ""))),
        "question": text_only(exercise.get("questionHtml", "")),
        "solution": text_only(exercise.get("solutionHtml", "")),
        "parts": [
            {
                "label": str(part.get("label", "")),
                "question": text_only(part.get("questionHtml", "")),
                "solution": text_only(part.get("solutionHtml", "")),
            }
            for part in exercise.get("parts", [])
        ],
    }
    payload = json.dumps(comparable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_numbers(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


parser = argparse.ArgumentParser()
parser.add_argument("--before", type=Path, required=True)
parser.add_argument("--after", type=Path, required=True)
args = parser.parse_args()

before = load_book(args.before)
after = load_book(args.after)
old = {str(item["number"]): item for item in before.get("exercises", [])}
new = {str(item["number"]): item for item in after.get("exercises", [])}

added = sorted(set(new) - set(old))
removed = sorted(set(old) - set(new))
changed = sorted(
    number
    for number in set(old) & set(new)
    if visible_content_fingerprint(old[number]) != visible_content_fingerprint(new[number])
)

old_by_question = {question_fingerprint(item): number for number, item in old.items()}
new_by_question = {question_fingerprint(item): number for number, item in new.items()}
moved = sorted(
    (old_number, new_by_question[fingerprint])
    for fingerprint, old_number in old_by_question.items()
    if fingerprint in new_by_question and new_by_question[fingerprint] != old_number
)

drafts = [str(value) for value in after.get("structure", {}).get("draftQuestions", [])]

print()
print("QUESTION CHANGE SUMMARY")
print(f"Before: {len(old)} public questions")
print(f"After:  {len(new)} public questions")
print(f"Added public numbers:   {format_numbers(added)}")
print(f"Removed public numbers: {format_numbers(removed)}")
print(f"Changed public numbers: {format_numbers(changed)}")
print(f"Draft headings:         {format_numbers(drafts)}")

if moved:
    print()
    print("WARNING: possible renumbering was detected:")
    for old_number, new_number in moved:
        print(f" - {old_number} may have moved to {new_number}")
    print("Inspect every shifted question, title, solution, and image before publishing.")

print("The summary is informational. The validated build continues regardless of change type.")
