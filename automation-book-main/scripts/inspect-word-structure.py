#!/usr/bin/env python3
"""Print Word body structure for maintaining the semantic importer."""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def attr(name: str) -> str:
    return f"{{{W}}}{name}"


def text_of(element: ET.Element) -> str:
    text = "".join(node.text or "" for node in element.findall(".//w:t", NS))
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--contains", default="", help="Only show text containing this value")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    args = parser.parse_args()

    with zipfile.ZipFile(args.source) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find("w:body", NS)
    if body is None:
        raise SystemExit("No Word document body found")

    paragraph_index = -1
    for body_index, element in enumerate(list(body)):
        if element.tag == attr("p"):
            paragraph_index += 1
        if body_index < args.start or (args.end is not None and body_index >= args.end):
            continue
        text = text_of(element)
        if args.contains and args.contains not in text:
            continue
        properties = element.find("w:pPr", NS) if element.tag == attr("p") else None
        style = properties.find("w:pStyle", NS) if properties is not None else None
        numbering = properties.find("w:numPr", NS) if properties is not None else None
        num_id = numbering.find("w:numId", NS) if numbering is not None else None
        level = numbering.find("w:ilvl", NS) if numbering is not None else None
        outline = properties.find("w:outlineLvl", NS) if properties is not None else None
        kind = "p" if element.tag == attr("p") else "tbl" if element.tag == attr("tbl") else "other"
        print(
            f"body={body_index:04d} para={paragraph_index:04d} kind={kind:5s} "
            f"style={style.get(attr('val'), '') if style is not None else '':12s} "
            f"num={num_id.get(attr('val'), '') if num_id is not None else '':4s} "
            f"lvl={level.get(attr('val'), '') if level is not None else '':2s} "
            f"outline={outline.get(attr('val'), '') if outline is not None else '':2s} "
            f"text={text[:180]}"
        )


if __name__ == "__main__":
    main()
