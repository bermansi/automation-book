#!/usr/bin/env python3
"""Build the public Hebrew course book from the canonical Word structure.

Unlike the legacy importer, this importer does not use Pandoc block numbers.
It reads the Word numbering/heading structure, inserts temporary semantic
markers, converts with Pandoc, and splits questions at those markers.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
import sys
import tempfile
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag
from lxml import etree


SCRIPT_DIR = Path(__file__).resolve().parent
LEGACY_PATH = SCRIPT_DIR / "build-from-word-pandoc.py"
legacy_spec = importlib.util.spec_from_file_location("automation_legacy_builder", LEGACY_PATH)
if legacy_spec is None or legacy_spec.loader is None:  # pragma: no cover
    raise SystemExit(f"Could not load shared build helpers from {LEGACY_PATH}")
legacy = importlib.util.module_from_spec(legacy_spec)
sys.modules[legacy_spec.name] = legacy
legacy_spec.loader.exec_module(legacy)

# The current Word stores the final ultrasonic wiring answer as floating Word
# artwork, which Pandoc does not expose.  Keep the verified flattened figure as
# a stable build asset, exactly like the other established Word-only diagrams.
if not any(item.key == "5-2-c" for item in legacy.WORD_VISUALS):
    legacy.WORD_VISUALS.append(
        legacy.WordVisualSpec(
            "5-2-c",
            "word-fixed-5-2-c.png",
            [],
            "חיבור חיישן אולטרסוני לבקר ארדואינו",
        )
    )


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W}
HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
CHAPTER_RE = re.compile(r"^פרק\s+([1-5])\b\s*(.*)$")
MANUAL_QUESTION_RE = re.compile(r"^(\d+\.\d+\.\d+[א-ת]?)\s+(.+)$")
CHAPTER4_SECTION_RE = re.compile(r"^(4\.\d+)\s+(.+)$")
CHAPTER4_QUESTION_RE = re.compile(r"^(\d+)\)\s+(.+)$")
CHAPTER5_EXAM_RE = re.compile(r"^5\.\d+\s+(.+)$")
CONTROLLER_TEXT_QUESTION_RE = re.compile(r"^\d+\)\s*")
MARKER_RE = re.compile(r"\[\[AB(?:CHAPTER|SECTION|QUESTION|PART|SOLUTION):[^\]]+\]\]")
LIST_FORMAT_MARKER = "[[ABLISTFMT:hebrew]]"

EXCLUDED_PUBLIC_SECTIONS = {"4.8"}

# Preserve the established public numbering in the controller subsection.
SPECIAL_QUESTION_NUMBERS = {
    ("1.6", 1): "1.6.1א",
    ("1.6", 2): "1.6.1ב",
    ("1.6", 3): "1.6.2א",
    ("1.6", 4): "1.6.2ב",
    ("1.6", 5): "1.6.3",
}

REGULAR_VISUALS: Dict[str, Sequence[str]] = {
    "1.1.3": ("1-1-3-solution",),
    "1.7.4": ("1-7-4",),
    "2.1.1": ("2-1-1-karnaugh",),
    "2.1.2": ("2-1-2-karnaugh",),
    "2.2.1": (
        "2-2-1-fill-karnaugh",
        "2-2-1-drain-karnaugh",
        "2-2-1-light-karnaugh",
    ),
    "2.2.2": ("2-2-2-karnaugh",),
    "2.2.3": ("2-2-3-karnaugh",),
}

PART_VISUALS: Dict[Tuple[str, str], Sequence[str]] = {
    ("1.7.1", "ד"): ("1-7-1-d",),
    ("1.7.2", "ד"): ("1-7-2-d",),
    ("1.7.3", "ב"): ("1-7-3-b",),
    ("1.7.5", "ג"): ("1-7-5-c",),
    ("5.2.1", "א"): ("5-2-a",),
    ("5.2.1", "ג"): ("5-2-c",),
    ("5.3.1", "ג"): ("5-3-c",),
    ("5.5.1", "ג"): ("5-5-button", "5-5-circuit"),
}


@dataclass
class ParagraphRecord:
    paragraph_index: int
    body_index: int
    element: etree._Element
    text: str
    style: str
    num_id: Optional[str]
    level: Optional[int]
    chapter: Optional[str] = None


@dataclass
class SectionRecord:
    id: str
    chapter: str
    title: str
    paragraph_index: int
    marker: str


@dataclass
class PartRecord:
    label: str
    title: str
    paragraph_index: int
    solution_index: int
    marker: str
    solution_marker: str


@dataclass
class QuestionRecord:
    id: str
    chapter: str
    section: str
    title: str
    paragraph_index: int
    marker: str
    end_marker: Optional[str] = None
    solution_index: Optional[int] = None
    solution_marker: Optional[str] = None
    parts: List[PartRecord] = field(default_factory=list)
    part_label_scheme: Optional[str] = None
    part_labels: List[str] = field(default_factory=list)
    solution_part_layout: Optional[str] = None
    draft: bool = False


@dataclass
class Structure:
    chapters: List[dict]
    sections: List[SectionRecord]
    questions: List[QuestionRecord]
    draft_question_ids: List[str]


def qn(local: str) -> str:
    return f"{{{W}}}{local}"


def word_text(element: etree._Element) -> str:
    text = "".join(node.text or "" for node in element.findall(".//w:t", NS))
    return re.sub(r"\s+", " ", text).strip()


def paragraph_properties(element: etree._Element) -> Tuple[str, Optional[str], Optional[int]]:
    properties = element.find("w:pPr", NS)
    if properties is None:
        return "", None, None
    style_node = properties.find("w:pStyle", NS)
    style = style_node.get(qn("val"), "") if style_node is not None else ""
    numbering = properties.find("w:numPr", NS)
    if numbering is None:
        return style, None, None
    num_node = numbering.find("w:numId", NS)
    level_node = numbering.find("w:ilvl", NS)
    num_id = num_node.get(qn("val")) if num_node is not None else None
    level = int(level_node.get(qn("val"), "0")) if level_node is not None else 0
    return style, num_id, level


def add_prefix(paragraph: etree._Element, marker: str) -> None:
    # Marker paragraphs must become independent Pandoc blocks.  Otherwise Word
    # list items can be wrapped in one large <ol>, making separate questions
    # share the same top-level HTML boundary.  This only changes the temporary
    # DOCX used during the build; the manager's source file is never modified.
    properties = paragraph.find("w:pPr", NS)
    numbering = properties.find("w:numPr", NS) if properties is not None else None
    if numbering is not None:
        properties.remove(numbering)
    text_node = paragraph.find(".//w:t", NS)
    if text_node is None:
        run = etree.Element(qn("r"))
        text_node = etree.SubElement(run, qn("t"))
        insert_at = 1 if properties is not None else 0
        paragraph.insert(insert_at, run)
    text_node.set(f"{{{XML}}}space", "preserve")
    text_node.text = marker + (text_node.text or "")


def add_list_format_marker(paragraph: etree._Element) -> None:
    """Mark a Hebrew Word list without changing its numbering properties."""
    text_node = paragraph.find(".//w:t", NS)
    if text_node is None:
        return
    text_node.set(f"{{{XML}}}space", "preserve")
    text_node.text = LIST_FORMAT_MARKER + (text_node.text or "")


def word_numbering_formats(archive: zipfile.ZipFile) -> Dict[Tuple[str, int], str]:
    """Return Word numbering formats keyed by (numId, level)."""
    numbering = etree.fromstring(archive.read("word/numbering.xml"))
    num_to_abstract = {
        node.get(qn("numId")): node.find("w:abstractNumId", NS).get(qn("val"))
        for node in numbering.findall("w:num", NS)
        if node.get(qn("numId")) is not None
        and node.find("w:abstractNumId", NS) is not None
    }
    formats: Dict[Tuple[str, int], str] = {}
    for abstract in numbering.findall("w:abstractNum", NS):
        abstract_id = abstract.get(qn("abstractNumId"))
        if abstract_id is None:
            continue
        for level in abstract.findall("w:lvl", NS):
            level_value = level.get(qn("ilvl"))
            format_node = level.find("w:numFmt", NS)
            if level_value is None or format_node is None:
                continue
            for num_id, mapped_abstract in num_to_abstract.items():
                if mapped_abstract == abstract_id:
                    formats[(num_id, int(level_value))] = format_node.get(qn("val"), "")
    return formats


def label_scheme(number_format: Optional[str]) -> Optional[str]:
    if number_format == "hebrew1":
        return "hebrew"
    if number_format in {"decimal", "decimalZero"}:
        return "numeric"
    return None


def sequential_labels(scheme: str, count: int) -> List[str]:
    if scheme == "hebrew":
        return [chr(ord("א") + index) for index in range(count)]
    if scheme == "numeric":
        return [str(index) for index in range(1, count + 1)]
    raise ValueError(f"Unsupported part-label scheme: {scheme}")


def source_part_label(
    record: ParagraphRecord,
    ordinal: int,
    numbering_formats: Dict[Tuple[str, int], str],
) -> str:
    scheme = label_scheme(numbering_formats.get((record.num_id, record.level)))
    if scheme is None:
        raise SystemExit(
            "Question parts must use either Hebrew letters or decimal numbers in Word; "
            f"could not read the format of: {record.text[:80]}"
        )
    return sequential_labels(scheme, ordinal)[-1]


def short_title(text: str, limit: int = 92) -> str:
    text = re.sub(r"^\d+(?:\.\d+)*(?:[א-ת])?[.)]?\s*", "", text).strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0]
    return clipped.rstrip(" ,;:.-") + "…"


def established_titles() -> Tuple[Dict[str, str], Dict[Tuple[str, str], str], Dict[str, str]]:
    question_titles = {item.number: item.title for item in legacy.EXERCISES}
    part_titles: Dict[Tuple[str, str], str] = {}
    for grouped in legacy.GROUPED_EXERCISES:
        question_titles[grouped.number] = grouped.title
        for part in grouped.parts:
            part_titles[(grouped.number, part.label)] = part.title
    section_titles = {
        section["id"]: section["title"]
        for chapter in legacy.CHAPTERS
        for section in chapter["sections"]
    }
    return question_titles, part_titles, section_titles


TITLE_OVERRIDES, PART_TITLE_OVERRIDES, SECTION_TITLE_OVERRIDES = established_titles()


def source_part_title(question_id: str, label: str, ordinal: int, text: str) -> str:
    # Historical title/visual overrides were keyed by Hebrew labels.  Falling
    # back by position keeps them attached if a manager changes the Word list
    # for the same question from Hebrew letters to decimal numbers.
    hebrew_position = chr(ord("א") + ordinal - 1)
    return PART_TITLE_OVERRIDES.get(
        (question_id, label),
        PART_TITLE_OVERRIDES.get((question_id, hebrew_position), short_title(text, 74)),
    )


def solution_marker(text: str) -> bool:
    return legacy.is_solution_marker(text)


def find_part_question(
    records: Sequence[ParagraphRecord],
    lower: int,
    solution_index: int,
) -> Optional[ParagraphRecord]:
    for record in reversed(records[lower:solution_index]):
        text = record.text.strip()
        if record.level != 0 or not HEBREW_RE.search(text) or len(text) < 8:
            continue
        if solution_marker(text) or text.startswith("פרק "):
            continue
        return record
    return None


def explicit_part_labels(records: Sequence[ParagraphRecord]) -> Tuple[Optional[str], List[str]]:
    """Read answer headings typed directly in Word, such as א. or 1."""
    hebrew: List[str] = []
    numeric: List[str] = []
    for record in records:
        text = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", record.text).strip()
        match = re.match(r"^([א-ת]|\d+)[.)]\s*", text)
        if not match:
            continue
        label = match.group(1)
        if label.isdigit():
            numeric.append(label)
        else:
            hebrew.append(label)
    if hebrew and numeric:
        return "mixed", hebrew + numeric
    if hebrew:
        return "hebrew", hebrew
    if numeric:
        return "numeric", numeric
    return None, []


def configure_single_solution_parts(
    question: QuestionRecord,
    records: Sequence[ParagraphRecord],
    solution_index: int,
    end_index: int,
    numbering_formats: Dict[Tuple[str, int], str],
) -> None:
    """Discover a part list whose answers are collected in one solution block.

    The question's Word list determines both the label scheme and the number of
    parts.  Answers may be headed by explicit text (``א.``, ``1.``) or by a
    second Word list.  This metadata lets the HTML stage correct explicit
    labels without confusing lists inside an answer with new question parts.
    """

    question_groups: Dict[Tuple[str, int], List[ParagraphRecord]] = defaultdict(list)
    for record in records[question.paragraph_index + 1 : solution_index]:
        if record.num_id is None or record.level != 0:
            continue
        scheme = label_scheme(numbering_formats.get((record.num_id, record.level)))
        if scheme is not None:
            question_groups[(record.num_id, record.level)].append(record)

    candidates = [items for items in question_groups.values() if len(items) >= 2]
    if not candidates:
        return

    # Include the solution marker itself: some Word questions begin their
    # collected solution with a heading such as "א. פתרון ...", which is both
    # the first answer label and the semantic solution boundary.
    answer_records = records[solution_index:end_index]
    explicit_scheme, explicit_labels = explicit_part_labels(answer_records)

    answer_groups: Dict[Tuple[str, int], List[ParagraphRecord]] = defaultdict(list)
    for record in answer_records:
        if record.num_id is None or record.level != 0:
            continue
        scheme = label_scheme(numbering_formats.get((record.num_id, record.level)))
        if scheme is not None:
            answer_groups[(record.num_id, record.level)].append(record)

    # The real part list is normally the last repeated level-zero list before
    # the solution.  Require a complete answer mapping before recording it.
    for question_items in sorted(candidates, key=lambda items: items[-1].paragraph_index, reverse=True):
        count = len(question_items)
        scheme = label_scheme(
            numbering_formats.get((question_items[0].num_id, question_items[0].level))
        )
        if scheme is None:
            continue

        if explicit_scheme in {"hebrew", "numeric"}:
            if explicit_labels == sequential_labels(explicit_scheme, count):
                question.part_label_scheme = scheme
                question.part_labels = sequential_labels(scheme, count)
                question.solution_part_layout = "explicit"
                return

        matching_answer_lists = []
        for answer_items in answer_groups.values():
            if len(answer_items) != count:
                continue
            answer_scheme = label_scheme(
                numbering_formats.get((answer_items[0].num_id, answer_items[0].level))
            )
            if answer_scheme == scheme:
                matching_answer_lists.append(answer_items)
        if matching_answer_lists:
            question.part_label_scheme = scheme
            question.part_labels = sequential_labels(scheme, count)
            question.solution_part_layout = "word-list"
            return


def semantic_structure(source: Path, marked_output: Path) -> Structure:
    with zipfile.ZipFile(source, "r") as archive:
        numbering_formats = word_numbering_formats(archive)
        root = etree.fromstring(archive.read("word/document.xml"))
        body = root.find(qn("body"))
        if body is None:
            raise SystemExit("The Word file has no document body")

        records: List[ParagraphRecord] = []
        paragraph_index = -1
        current_chapter: Optional[str] = None
        for body_index, element in enumerate(list(body)):
            if element.tag != qn("p"):
                continue
            paragraph_index += 1
            text = word_text(element)
            style, num_id, level = paragraph_properties(element)
            match = CHAPTER_RE.match(text)
            if style == "Heading1" and match:
                current_chapter = match.group(1)
            records.append(
                ParagraphRecord(
                    paragraph_index,
                    body_index,
                    element,
                    text,
                    style,
                    num_id,
                    level,
                    current_chapter,
                )
            )

        chapters: List[dict] = []
        sections: List[SectionRecord] = []
        questions: List[QuestionRecord] = []
        structural_num: Dict[str, str] = {}
        section_counter: Dict[str, int] = defaultdict(int)
        current_section: Dict[str, str] = {}
        question_counter: Dict[str, int] = defaultdict(int)
        chapter5_counter = 0
        seen_sections: set[str] = set()
        seen_questions: set[str] = set()
        chapter_markers: List[Tuple[int, str]] = []

        def add_section(section_id: str, chapter: str, title: str, record: ParagraphRecord) -> None:
            if section_id in seen_sections:
                return
            marker = f"[[ABSECTION:{section_id}]]"
            sections.append(
                SectionRecord(
                    section_id,
                    chapter,
                    SECTION_TITLE_OVERRIDES.get(section_id, short_title(title)),
                    record.paragraph_index,
                    marker,
                )
            )
            seen_sections.add(section_id)
            add_prefix(record.element, marker)

        def add_question(question_id: str, chapter: str, section_id: str, title: str, record: ParagraphRecord) -> None:
            if question_id in seen_questions:
                raise SystemExit(f"Duplicate question number discovered in Word: {question_id}")
            marker = f"[[ABQUESTION:{question_id}]]"
            questions.append(
                QuestionRecord(
                    question_id,
                    chapter,
                    section_id,
                    TITLE_OVERRIDES.get(question_id, short_title(title)),
                    record.paragraph_index,
                    marker,
                )
            )
            seen_questions.add(question_id)
            add_prefix(record.element, marker)

        for record in records:
            text = record.text.strip()
            chapter_match = CHAPTER_RE.match(text)
            if record.style == "Heading1" and chapter_match:
                chapter = chapter_match.group(1)
                title = chapter_match.group(2).strip()
                marker = f"[[ABCHAPTER:{chapter}]]"
                chapter_markers.append((record.paragraph_index, marker))
                add_prefix(record.element, marker)
                chapters.append({"number": chapter, "title": title})
                continue

            chapter = record.chapter
            if chapter in {"1", "2", "3"}:
                explicit = MANUAL_QUESTION_RE.match(text)
                if explicit and explicit.group(1).startswith(chapter + "."):
                    question_id = explicit.group(1)
                    section_id = question_id.rsplit(".", 1)[0]
                    question_counter[section_id] = max(
                        question_counter[section_id],
                        int(re.match(r"\d+", question_id.rsplit(".", 1)[1]).group()),
                    )
                    add_question(question_id, chapter, section_id, explicit.group(2), record)
                    continue

                if chapter not in structural_num and record.level == 1 and record.num_id:
                    structural_num[chapter] = record.num_id
                if record.num_id != structural_num.get(chapter):
                    continue
                if record.level == 1:
                    section_counter[chapter] += 1
                    section_id = f"{chapter}.{section_counter[chapter]}"
                    current_section[chapter] = section_id
                    add_section(section_id, chapter, text, record)
                elif record.level == 2 and current_section.get(chapter):
                    section_id = current_section[chapter]
                    # Section 1.6 is intentionally laid out as three controller
                    # headings (P, PD, PI) containing five real questions.  The
                    # real question starts are discovered below from their
                    # local numbered-list paragraphs.
                    if section_id == "1.6":
                        continue
                    question_counter[section_id] += 1
                    ordinal = question_counter[section_id]
                    question_id = SPECIAL_QUESTION_NUMBERS.get(
                        (section_id, ordinal), f"{section_id}.{ordinal}"
                    )
                    add_question(question_id, chapter, section_id, text, record)
                continue

            if chapter == "4":
                section_match = CHAPTER4_SECTION_RE.match(text)
                if section_match:
                    section_id = section_match.group(1)
                    current_section[chapter] = section_id
                    add_section(section_id, chapter, section_match.group(2), record)
                    continue
                question_match = CHAPTER4_QUESTION_RE.match(text)
                section_id = current_section.get(chapter)
                if question_match and section_id:
                    ordinal = int(question_match.group(1))
                    question_id = f"{section_id}.{ordinal}"
                    question_counter[section_id] = max(question_counter[section_id], ordinal)
                    add_question(question_id, chapter, section_id, question_match.group(2), record)
                continue

            if chapter == "5":
                exam_match = CHAPTER5_EXAM_RE.match(text)
                if exam_match:
                    chapter5_counter += 1
                    section_id = f"5.{chapter5_counter}"
                    current_section[chapter] = section_id
                    title = exam_match.group(1).strip()
                    add_section(section_id, chapter, title, record)
                    add_question(f"{section_id}.1", chapter, section_id, title, record)

        # Preserve the established five public controller questions.  In the
        # canonical Word file, the two P questions begin with literal "1)" and
        # "2)" text; the PD/PI questions use dedicated level-zero Word lists.
        controller_section = next((item for item in sections if item.id == "1.6"), None)
        next_section = next((item for item in sections if item.id == "1.7"), None)
        if controller_section is not None:
            upper = next_section.paragraph_index if next_section is not None else len(records)
            controller_starts = [
                record
                for record in records[controller_section.paragraph_index + 1 : upper]
                if CONTROLLER_TEXT_QUESTION_RE.match(record.text)
                or (record.level == 0 and record.num_id in {"25", "26"})
            ]
            expected_ids = ["1.6.1א", "1.6.1ב", "1.6.2א", "1.6.2ב", "1.6.3"]
            if len(controller_starts) != len(expected_ids):
                raise SystemExit(
                    "Section 1.6 must contain five controller questions; "
                    f"discovered {len(controller_starts)}"
                )
            for question_id, record in zip(expected_ids, controller_starts):
                add_question(question_id, "1", "1.6", record.text, record)

        boundaries: List[Tuple[int, str]] = chapter_markers
        boundaries += [(section.paragraph_index, section.marker) for section in sections]
        boundaries += [(question.paragraph_index, question.marker) for question in questions]
        boundaries.sort(key=lambda item: item[0])

        for question in questions:
            later = [item for item in boundaries if item[0] > question.paragraph_index]
            end_index = later[0][0] if later else len(records)
            question.end_marker = later[0][1] if later else None

            # A course manager can safely remove a question from the public
            # book without renumbering everything that follows it: keep the
            # styled question heading, and remove the question body and its
            # solution block.  Such an empty heading is a deliberate draft.
            # Detect it before the historical multi-part special cases below,
            # which otherwise expect their old part structure to be present.
            body_records = records[question.paragraph_index + 1 : end_index]
            if not any(record.text.strip() for record in body_records):
                question.draft = True
                continue

            # Two archived exams contain six lettered parts, but a few worked
            # answers begin immediately after the part instead of using a
            # standalone "פתרון" line.  Their six question paragraphs share
            # one Word list ID, so discover that repeated list semantically and
            # use the next paragraph as the implicit answer boundary when
            # needed.
            if question.id in {"1.7.1", "1.7.5"}:
                level_zero_by_list: Dict[str, List[ParagraphRecord]] = defaultdict(list)
                for record in records[question.paragraph_index + 1 : end_index]:
                    if record.level == 0 and record.num_id:
                        level_zero_by_list[record.num_id].append(record)
                six_part_lists = [items for items in level_zero_by_list.values() if len(items) == 6]
                if len(six_part_lists) != 1:
                    raise SystemExit(
                        f"Expected one six-part Word list in archived exam {question.id}; "
                        f"found {len(six_part_lists)}"
                    )
                candidates = six_part_lists[0]
                for index, candidate in enumerate(candidates):
                    part_end = candidates[index + 1].paragraph_index if index + 1 < len(candidates) else end_index
                    explicit_solution = next(
                        (
                            record
                            for record in records[candidate.paragraph_index + 1 : part_end]
                            if solution_marker(record.text)
                        ),
                        None,
                    )
                    solution = explicit_solution or records[candidate.paragraph_index + 1]
                    label = source_part_label(candidate, index + 1, numbering_formats)
                    part_marker = f"[[ABPART:{question.id}:{label}]]"
                    solution_token = f"[[ABSOLUTION:{question.id}:{label}]]"
                    add_prefix(candidate.element, part_marker)
                    add_prefix(solution.element, solution_token)
                    question.parts.append(
                        PartRecord(
                            label,
                            source_part_title(question.id, label, index + 1, candidate.text),
                            candidate.paragraph_index,
                            solution.paragraph_index,
                            part_marker,
                            solution_token,
                        )
                    )
                continue

            solutions = [
                record
                for record in records[question.paragraph_index + 1 : end_index]
                if solution_marker(record.text)
            ]
            # The reactor exercise is a worked design example: Word places the
            # full worked content immediately after its title and intentionally
            # has no literal "פתרון" paragraph.  Preserve that documented
            # convention while requiring normal new questions to include the
            # explicit solution marker.
            if not solutions and question.id == "2.2.1":
                implicit_solution = next(
                    (
                        record
                        for record in records[question.paragraph_index + 1 : end_index]
                        if record.text.strip()
                    ),
                    None,
                )
                if implicit_solution is not None:
                    marker = f"[[ABSOLUTION:{question.id}:main]]"
                    question.solution_index = implicit_solution.paragraph_index
                    question.solution_marker = marker
                    add_prefix(implicit_solution.element, marker)
                    continue
            if not solutions:
                question.draft = True
                continue

            grouped = len(solutions) > 1 or question.chapter == "5"
            if not grouped:
                solution = solutions[0]
                marker = f"[[ABSOLUTION:{question.id}:main]]"
                question.solution_index = solution.paragraph_index
                question.solution_marker = marker
                add_prefix(solution.element, marker)
                configure_single_solution_parts(
                    question,
                    records,
                    solution.paragraph_index,
                    end_index,
                    numbering_formats,
                )
                continue

            previous_solution = question.paragraph_index
            used_candidates: set[int] = set()
            for part_number, solution in enumerate(solutions, start=1):
                candidate = find_part_question(records, previous_solution + 1, solution.paragraph_index)
                if candidate is None or candidate.paragraph_index in used_candidates:
                    raise SystemExit(
                        f"Could not identify the question text before solution {part_number} of {question.id}"
                    )
                used_candidates.add(candidate.paragraph_index)
                label = source_part_label(candidate, part_number, numbering_formats)
                part_marker = f"[[ABPART:{question.id}:{label}]]"
                solution_token = f"[[ABSOLUTION:{question.id}:{label}]]"
                add_prefix(candidate.element, part_marker)
                add_prefix(solution.element, solution_token)
                question.parts.append(
                    PartRecord(
                        label,
                        source_part_title(question.id, label, part_number, candidate.text),
                        candidate.paragraph_index,
                        solution.paragraph_index,
                        part_marker,
                        solution_token,
                    )
                )
                previous_solution = solution.paragraph_index

        # Pandoc preserves decimal and Latin list formats in HTML, but it drops
        # Word's Hebrew numbering format. Add a temporary marker to list items
        # that still have their numbering properties so the HTML postprocessor
        # can restore א, ב, ג... exactly as written in Word.
        for record in records:
            if record.num_id is None or record.level is None:
                continue
            properties = record.element.find("w:pPr", NS)
            if properties is None or properties.find("w:numPr", NS) is None:
                continue
            if numbering_formats.get((record.num_id, record.level)) == "hebrew1":
                add_list_format_marker(record.element)

        replacement = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")
        marked_output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(marked_output, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for item in archive.infolist():
                data = replacement if item.filename == "word/document.xml" else archive.read(item.filename)
                output.writestr(item, data)

    published_by_section = defaultdict(int)
    for question in questions:
        if not question.draft and question.section not in EXCLUDED_PUBLIC_SECTIONS:
            published_by_section[question.section] += 1

    chapter_data: List[dict] = []
    for chapter in chapters:
        chapter_sections = []
        for section in sections:
            if section.chapter != chapter["number"] or section.id in EXCLUDED_PUBLIC_SECTIONS:
                continue
            if not published_by_section[section.id]:
                continue
            chapter_sections.append({"id": section.id, "title": section.title})
        chapter_data.append(
            {
                "number": chapter["number"],
                "id": f"chapter-{chapter['number']}",
                "title": chapter["title"],
                "sections": chapter_sections,
            }
        )

    return Structure(
        chapter_data,
        sections,
        questions,
        [question.id for question in questions if question.draft],
    )


@dataclass
class MarkerPoint:
    block_index: int
    paragraph: Tag


def marker_point(children: Sequence[Tag], marker: str) -> MarkerPoint:
    for block_index, block in enumerate(children):
        node = block.find(string=lambda value: isinstance(value, str) and marker in value)
        if node is None:
            continue
        paragraph = node.find_parent("p")
        if paragraph is None:
            paragraph = node.parent
        if not isinstance(paragraph, Tag):
            break
        return MarkerPoint(block_index, paragraph)
    raise SystemExit(f"Pandoc output is missing semantic marker {marker}")


def clean_marker_paragraph(paragraph: Tag, *, solution: bool = False) -> str:
    soup = BeautifulSoup(str(paragraph), "html.parser")
    for node in list(soup.find_all(string=True)):
        original = str(node)
        cleaned = MARKER_RE.sub("", original)
        if solution:
            cleaned = re.sub(r"^\s*פתרון\s*:?[\u200e\u200f\s]*", "", cleaned, count=1)
        if cleaned != original:
            if cleaned:
                node.replace_with(NavigableString(cleaned))
            else:
                node.extract()
    result = str(soup).strip()
    if not soup.get_text(" ", strip=True) and not soup.find(["img", "table"]):
        return ""
    return result


def join_html(first: str, middle: Iterable[Tag]) -> str:
    remainder = legacy.clean_fragment(middle)
    return "\n".join(part for part in (first, remainder) if part and part.strip())


def end_block(children: Sequence[Tag], marker: Optional[str]) -> int:
    return marker_point(children, marker).block_index if marker else len(children)


def question_sort_key(question: QuestionRecord) -> Tuple[int, ...]:
    values = []
    for part in question.id.split("."):
        match = re.match(r"\d+", part)
        values.append(int(match.group()) if match else 0)
    return tuple(values)


def build_exercises(
    structure: Structure,
    children: Sequence[Tag],
    visuals: Dict[str, legacy.WordVisualSpec],
) -> List[dict]:
    exercises: List[dict] = []
    for question in sorted(structure.questions, key=question_sort_key):
        if question.draft or question.section in EXCLUDED_PUBLIC_SECTIONS:
            continue
        question_point = marker_point(children, question.marker)
        question_end = end_block(children, question.end_marker)

        if not question.parts:
            if not question.solution_marker:
                raise SystemExit(f"Published question has no solution marker: {question.id}")
            solution_point = marker_point(children, question.solution_marker)
            question_html = join_html(
                clean_marker_paragraph(question_point.paragraph),
                children[question_point.block_index + 1 : solution_point.block_index],
            )
            solution_html = join_html(
                clean_marker_paragraph(solution_point.paragraph, solution=True),
                children[solution_point.block_index + 1 : question_end],
            )
            solution_html = legacy.attach_word_visuals(
                solution_html,
                REGULAR_VISUALS.get(question.id, ()),
                visuals,
            )
            if not question_html.strip() or not solution_html.strip():
                raise SystemExit(f"Empty question or solution after semantic import: {question.id}")
            exercise = {
                "id": legacy.exercise_id(question.id),
                "number": question.id,
                "section": question.section,
                "title": question.title,
                "questionHtml": question_html,
                "solutionHtml": solution_html,
            }
            if question.part_labels:
                exercise["partLabelScheme"] = question.part_label_scheme
                exercise["partLabels"] = question.part_labels
                exercise["solutionPartLayout"] = question.solution_part_layout
            exercises.append(exercise)
            continue

        first_part_point = marker_point(children, question.parts[0].marker)
        intro_html = legacy.clean_fragment(
            children[question_point.block_index + 1 : first_part_point.block_index]
        )
        if not intro_html.strip():
            intro_html = "<p>השאלה מחולקת לסעיפים. לכל סעיף פתרון שנפתח בנפרד.</p>"
        parts = []
        for index, part in enumerate(question.parts):
            part_point = marker_point(children, part.marker)
            solution_point = marker_point(children, part.solution_marker)
            next_part_block = (
                marker_point(children, question.parts[index + 1].marker).block_index
                if index + 1 < len(question.parts)
                else question_end
            )
            part_question_html = join_html(
                clean_marker_paragraph(part_point.paragraph),
                children[part_point.block_index + 1 : solution_point.block_index],
            )
            part_solution_html = join_html(
                clean_marker_paragraph(solution_point.paragraph, solution=True),
                children[solution_point.block_index + 1 : next_part_block],
            )
            visual_keys = PART_VISUALS.get((question.id, part.label))
            if visual_keys is None:
                visual_keys = PART_VISUALS.get((question.id, chr(ord("א") + index)), ())
            part_solution_html = legacy.attach_word_visuals(
                part_solution_html,
                visual_keys,
                visuals,
            )
            if not part_question_html.strip() or not part_solution_html.strip():
                raise SystemExit(f"Empty content in {question.id} part {part.label}")
            parts.append(
                {
                    "label": part.label,
                    "title": part.title,
                    "questionHtml": part_question_html,
                    "solutionHtml": part_solution_html,
                }
            )
        exercises.append(
            {
                "id": legacy.exercise_id(question.id),
                "number": question.id,
                "section": question.section,
                "title": question.title,
                "questionHtml": intro_html,
                "parts": parts,
            }
        )

    return exercises


def preserve_word_list_formats(soup: BeautifulSoup) -> None:
    """Restore Hebrew list markers that Pandoc cannot express by itself."""
    for node in list(soup.find_all(string=lambda value: isinstance(value, str) and LIST_FORMAT_MARKER in value)):
        parent_list = node.find_parent("ol")
        if parent_list is not None:
            classes = set(parent_list.get("class", []))
            classes.add("word-list-hebrew")
            parent_list["class"] = sorted(classes)
            parent_list.attrs.pop("type", None)
        cleaned = str(node).replace(LIST_FORMAT_MARKER, "")
        if cleaned:
            node.replace_with(NavigableString(cleaned))
        else:
            node.extract()

    if LIST_FORMAT_MARKER in soup.get_text(" "):
        raise SystemExit("Could not remove all temporary Word list-format markers")


def normalize_explicit_solution_labels(
    solution_html: str,
    expected_scheme: Optional[str],
    expected_labels: Sequence[str],
    solution_layout: Optional[str],
) -> str:
    """Make collected answer labels follow the question's Word list.

    For an all-answers-at-the-end layout, the question list is authoritative.
    Explicit answer headings are rewritten from Hebrew to decimal or vice
    versa when necessary.  Ordered lists inside those explicit answers are
    supporting content rather than another set of parts, so lists using the
    same label scheme are displayed as bullets.
    """

    if solution_layout != "explicit" or expected_scheme is None or len(expected_labels) < 2:
        return solution_html

    solution_soup = BeautifulSoup(solution_html, "html.parser")
    labelled_nodes: List[Tuple[NavigableString, str]] = []
    for paragraph in solution_soup.find_all("p"):
        if paragraph.find_parent(["li", "table"]):
            continue
        for node in paragraph.find_all(string=True):
            original = str(node)
            match = re.match(
                r"^(\s*[\u200e\u200f\u202a-\u202e\u2066-\u2069]*)([א-ת]|\d+)([.)])",
                original,
            )
            if match:
                labelled_nodes.append((node, match.group(2)))
                break

    found_labels = [label for _, label in labelled_nodes]
    found_scheme = None
    if found_labels and all(label.isdigit() for label in found_labels):
        found_scheme = "numeric"
    elif found_labels and all(not label.isdigit() for label in found_labels):
        found_scheme = "hebrew"

    if found_scheme is None or found_labels != sequential_labels(found_scheme, len(expected_labels)):
        raise SystemExit(
            "Could not match the collected solution headings to the question parts. "
            f"Expected {len(expected_labels)} sequential headings; found {found_labels}."
        )

    for (node, _), replacement in zip(labelled_nodes, expected_labels):
        original = str(node)
        updated = re.sub(
            r"^(\s*[\u200e\u200f\u202a-\u202e\u2066-\u2069]*)([א-ת]|\d+)([.)])",
            lambda match: match.group(1) + replacement + match.group(3),
            original,
            count=1,
        )
        node.replace_with(NavigableString(updated))

    for ordered in solution_soup.find_all("ol"):
        scheme = "hebrew" if "word-list-hebrew" in ordered.get("class", []) else "numeric"
        if scheme != expected_scheme:
            continue
        ordered.name = "ul"
        classes = [name for name in ordered.get("class", []) if name != "word-list-hebrew"]
        if classes:
            ordered["class"] = classes
        else:
            ordered.attrs.pop("class", None)
        ordered.attrs.pop("start", None)
        ordered.attrs.pop("type", None)

    return str(solution_soup).strip()


def postprocess_exercise_html(exercises: List[dict]) -> None:
    """Apply the established RTL/math cleanup after semantic markers are removed.

    Running this before marker discovery can split an ASCII marker across
    several inline spans, so it deliberately happens on the finished fragments.
    """

    def process(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        legacy.postprocess_soup(soup)
        return str(soup).strip()

    for exercise in exercises:
        for field_name in ("questionHtml", "solutionHtml"):
            if field_name in exercise:
                exercise[field_name] = process(exercise[field_name])
        if "questionHtml" in exercise and "solutionHtml" in exercise:
            exercise["solutionHtml"] = normalize_explicit_solution_labels(
                exercise["solutionHtml"],
                exercise.get("partLabelScheme"),
                exercise.get("partLabels", ()),
                exercise.get("solutionPartLayout"),
            )
        for part in exercise.get("parts", []):
            for field_name in ("questionHtml", "solutionHtml"):
                if field_name in part:
                    part[field_name] = process(part[field_name])


def build_data(
    original_source: Path,
    marked_source: Path,
    structure: Structure,
    html_path: Path,
    temp_dir: Path,
    docs_dir: Path,
) -> dict:
    raw_html = legacy.clean_raw_pandoc_html(html_path.read_text(encoding="utf-8"))
    soup = BeautifulSoup(raw_html, "html.parser")
    preserve_word_list_formats(soup)
    legacy.normalize_media(temp_dir, docs_dir, soup)
    body = soup.body or soup
    children = [child for child in body.children if isinstance(child, Tag)]
    visuals = legacy.render_word_visuals(original_source, docs_dir, temp_dir)
    exercises = build_exercises(structure, children, visuals)
    postprocess_exercise_html(exercises)
    legacy.rasterize_image_processing_matrices(exercises, docs_dir)
    legacy.stabilize_all_exercise_images(exercises, docs_dir)

    return {
        "source": "private Word source (included only in the local handoff ZIP; ignored by Git)",
        "build": "semantic-word-structure-v1-pandoc-word-drawings-rtl",
        "notes": (
            "Questions are discovered from the canonical Word hierarchy. "
            "Only sections containing complete published questions are shown. "
            "Section 4.8 is intentionally excluded from publication."
        ),
        "structure": {
            "discoveredQuestions": len(structure.questions),
            "publishedQuestions": len(exercises),
            "draftQuestions": structure.draft_question_ids,
            "excludedSections": sorted(EXCLUDED_PUBLIC_SECTIONS),
        },
        "chapters": structure.chapters,
        "exercises": exercises,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Canonical private automation-book DOCX")
    parser.add_argument("--out", type=Path, default=Path("docs"))
    args = parser.parse_args()
    if not args.source.exists():
        raise SystemExit(f"Word source not found: {args.source}")
    args.out.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as directory:
        temp_dir = Path(directory)
        marked_source = temp_dir / "semantic-source.docx"
        structure = semantic_structure(args.source, marked_source)
        html_path = legacy.run_pandoc(marked_source, temp_dir)
        data = build_data(
            args.source,
            marked_source,
            structure,
            html_path,
            temp_dir,
            args.out,
        )
    legacy.write_book_data(data, args.out)
    # Pruning is deliberately the final filesystem operation. Pandoc extracts
    # every image embedded in Word, while only the images referenced by public
    # book data may remain in docs/media.
    legacy.prune_unused_media(data, args.out)
    # Match the validator's exact view of the published JavaScript file. Some
    # Word images remain in a reused docs/media directory after conversion;
    # only references in the final public book data belong in the website.
    published_js = (args.out / "assets" / "book-data.js").read_text(encoding="utf-8")
    published_media = set(re.findall(r"media/([^\"'\\\\]+)", published_js))
    for media_path in (args.out / "media").iterdir():
        if media_path.is_file() and media_path.name not in published_media:
            media_path.unlink()
    print(
        f"Built {len(data['exercises'])} public questions from {args.source}; "
        f"draft headings: {len(data['structure']['draftQuestions'])}."
    )


if __name__ == "__main__":
    main()
