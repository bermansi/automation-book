#!/usr/bin/env python3
"""Print a manager-friendly summary of changes between two generated books."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path


def load_book(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw.removeprefix("window.BOOK_DATA = ").rstrip(" ;\n"))


def text_only(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def question_fingerprint(exercise: dict) -> str:
    pieces = [text_only(exercise.get("questionHtml", ""))]
    for part in exercise.get("parts", []):
        pieces.append(text_only(part.get("questionHtml", "")))
    return hashlib.sha256("\n".join(pieces).encode("utf-8")).hexdigest()


def full_fingerprint(exercise: dict) -> str:
    comparable = {
        "title": exercise.get("title"),
        "questionHtml": exercise.get("questionHtml"),
        "solutionHtml": exercise.get("solutionHtml"),
        "parts": exercise.get("parts", []),
    }
    payload = json.dumps(comparable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_numbers(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


parser = argparse.ArgumentParser()
parser.add_argument("--before", type=Path, required=True)
parser.add_argument("--after", type=Path, required=True)
parser.add_argument("--operation", choices=["edit", "add", "delete", "mixed"], required=True)
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
    if full_fingerprint(old[number]) != full_fingerprint(new[number])
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

operation_mismatch = False
if args.operation == "edit":
    if added or removed:
        operation_mismatch = True
        print("ERROR: You selected EDIT ONLY, but public question numbers were added or removed.")
elif args.operation == "add":
    if not added:
        operation_mismatch = True
        print("ERROR: You selected ADD ONLY, but no new public question number was detected.")
    elif removed or changed:
        operation_mismatch = True
        print("ERROR: You selected ADD ONLY, but edits or deletions were also detected.")
elif args.operation == "delete":
    if not removed:
        operation_mismatch = True
        print("ERROR: You selected DELETE ONLY, but no public question number was removed.")
    elif added or changed:
        operation_mismatch = True
        print("ERROR: You selected DELETE ONLY, but additions or edits were also detected.")
# Mixed mode intentionally accepts any combination. The detailed summary above
# remains the review gate and the full site validator still runs afterwards.

if operation_mismatch:
    print("The staged build was stopped so the existing docs folder stays unchanged.")
    raise SystemExit(2)
