"""Week 2 deterministic baseline V2: PDF extraction and reference comparison.

Run from 02_extracao_piloto: python pdf_baseline_v2.py
Inputs: the original 2015 Balanço Social PDF and development reference CSV.
Outputs: baseline_v2_results.csv, baseline_v2_comparison.csv and console summary.
Only five DEVELOPMENT institutions are considered. No held-out cases, LLM or API.
"""
from __future__ import annotations

import csv
from pathlib import Path
import re
import sys

import pymupdf

HERE = Path(__file__).resolve().parent
PDF_PATH = HERE.parent / "2_BALANCO-SOCIAL-CAP-H-ADP.PDF"
REFERENCE_PATH = HERE / "table1_source_A_EN.csv"
OUTPUT_PATH = HERE / "baseline_v2_results.csv"
COMPARISON_PATH = HERE / "baseline_v2_comparison.csv"
PDF_PAGE = 14
REFERENCE_YEAR = 2015

# Scope identifiers, not expected numbers: all numeric counts come from the PDF.
INSTITUTIONS = (
    ("Ministry of Education and Sports", "Ministério Da Educação e Desporto"),
    ("Ministry of Internal Administration", "Ministério Da Administração Interna"),
    ("Ministry of Rural Development", "Ministério Do Desenvolvimento Rural"),
    ("Ministry of Health", "Ministério Da Saúde"),
    ("Ministry of Finance and Planning", "Ministério Das Finanças e do Planeamento"),
)

RESULT_FIELDS = [
    "Institution", "Source Institution Label", "Female Employees", "Male Employees",
    "Reported Total", "Reported Share (%)", "Calculated Total", "Difference",
    "Arithmetic Status", "Reference Year", "Source Filename", "PDF Page", "Printed Page",
    "Source Table", "Extraction Status", "Evidence Text",
]
COMPARISON_FIELDS = [
    "Institution", "Extraction Status", "Reference Status", "Reference Field Matches",
    "Field Differences", "PDF Arithmetic Status", "Reference Arithmetic Status",
    "Comparison Outcome",
]


def parse_record(blocks: list[str], institution_en: str, institution_pt: str) -> dict:
    matches = [block for block in blocks if institution_pt.casefold() in block.casefold()]
    record = {k: "" for k in RESULT_FIELDS}
    record.update({
        "Institution": institution_en,
        "Reference Year": REFERENCE_YEAR,
        "Source Filename": PDF_PATH.name,
        "PDF Page": PDF_PAGE,
        "Printed Page": 2,
        "Source Table": "Table 1",
    })
    if len(matches) != 1:
        record["Extraction Status"] = "MISSING" if not matches else "AMBIGUOUS"
        record["Evidence Text"] = f"Matching text blocks: {len(matches)}"
        return record

    lines = [line.strip() for line in matches[0].splitlines() if line.strip()]
    try:
        pos = next(i for i, line in enumerate(lines) if institution_pt.casefold() in line.casefold())
        fields = lines[pos + 1:pos + 5]
        if len(fields) != 4:
            raise ValueError("Expected four numeric fields")
        if not all(re.fullmatch(r"\d+", field) for field in fields[:3]):
            raise ValueError("Invalid employee counts")
        if not re.fullmatch(r"\d+(?:,\d+)?%", fields[3]):
            raise ValueError("Invalid percentage")
        female, male, reported = map(int, fields[:3])
        share = float(fields[3].removesuffix("%").replace(",", "."))
    except (ValueError, StopIteration) as exc:
        record["Extraction Status"] = "PARSE_REVIEW"
        record["Evidence Text"] = f"{exc}: {' | '.join(lines)}"
        return record

    calculated = female + male
    record.update({
        "Source Institution Label": lines[pos],
        "Female Employees": female,
        "Male Employees": male,
        "Reported Total": reported,
        "Reported Share (%)": share,
        "Calculated Total": calculated,
        "Difference": reported - calculated,
        "Arithmetic Status": "MATCH" if reported == calculated else "REVIEW",
        "Extraction Status": "PARSED",
        "Evidence Text": " | ".join(lines[pos:pos + 5]),
    })
    return record


def load_reference() -> dict[str, dict]:
    with REFERENCE_PATH.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    reference = {}
    for row in rows:
        name = row["Institution (English translation)"].strip()
        if name in reference:
            raise ValueError(f"Duplicate reference institution: {name}")
        reference[name] = row
    return reference


def compare(record: dict, reference: dict[str, dict]) -> dict:
    name = record["Institution"]
    result = {key: "" for key in COMPARISON_FIELDS}
    result.update({
        "Institution": name,
        "Extraction Status": record["Extraction Status"],
        "PDF Arithmetic Status": record["Arithmetic Status"],
    })
    if name not in reference:
        result.update({"Reference Status": "MISSING", "Comparison Outcome": "REVIEW"})
        return result
    ref = reference[name]
    result["Reference Status"] = "FOUND"
    result["Reference Arithmetic Status"] = ref["Validation Status"]
    if record["Extraction Status"] != "PARSED":
        result["Comparison Outcome"] = "REVIEW"
        return result
    checks = {
        "Female Employees": (record["Female Employees"], int(ref["Female Employees"])),
        "Male Employees": (record["Male Employees"], int(ref["Male Employees"])),
        "Reported Total": (record["Reported Total"], int(ref["Reported Total"])),
        "Reported Share (%)": (record["Reported Share (%)"], float(ref["Reported Share (%)"])),
        "Reference Year": (record["Reference Year"], int(ref["Reference Year"])),
        "PDF Page": (record["PDF Page"], int(ref["PDF Page"])),
        "Source Filename": (record["Source Filename"], ref["Source Filename"]),
    }
    differences = [f"{field}: PDF={pdf_value}, reference={ref_value}"
                   for field, (pdf_value, ref_value) in checks.items()
                   if pdf_value != ref_value]
    result["Reference Field Matches"] = f"{len(checks) - len(differences)}/{len(checks)}"
    result["Field Differences"] = "; ".join(differences)
    status_matches = record["Arithmetic Status"] == ref["Validation Status"]
    result["Comparison Outcome"] = "MATCH" if not differences and status_matches else "REVIEW"
    if not status_matches:
        result["Field Differences"] += ("; " if differences else "") + "Arithmetic status differs"
    return result


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    for path in (PDF_PATH, REFERENCE_PATH):
        if not path.is_file():
            print(f"ERROR: Required source not found: {path}", file=sys.stderr)
            return 1
    try:
        with pymupdf.open(PDF_PATH) as document:
            if len(document) < PDF_PAGE:
                raise ValueError(f"PDF has fewer than {PDF_PAGE} pages")
            blocks = [block[4] for block in document[PDF_PAGE - 1].get_text("blocks")]
        reference = load_reference()
        records = [parse_record(blocks, en, pt) for en, pt in INSTITUTIONS]
        comparisons = [compare(row, reference) for row in records]
        write_csv(OUTPUT_PATH, RESULT_FIELDS, records)
        write_csv(COMPARISON_PATH, COMPARISON_FIELDS, comparisons)
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    extracted = sum(row["Extraction Status"] == "PARSED" for row in records)
    matched = sum(row["Comparison Outcome"] == "MATCH" for row in comparisons)
    arithmetic_reviews = sum(row["Arithmetic Status"] == "REVIEW" for row in records)
    print(f"Source PDF: {PDF_PATH.name} | Year: {REFERENCE_YEAR} | Page: {PDF_PAGE}")
    print(f"Extracted records: {extracted}/{len(records)}")
    print(f"Reference comparisons matching: {matched}/{len(comparisons)}")
    print(f"Arithmetic review flags: {arithmetic_reviews}")
    print(f"Results CSV: {OUTPUT_PATH.name}")
    print(f"Comparison CSV: {COMPARISON_PATH.name}")
    print("Note: Development data only; no independent accuracy claim.")
    return 0 if extracted == len(records) and matched == len(comparisons) else 2


if __name__ == "__main__":
    sys.exit(main())
