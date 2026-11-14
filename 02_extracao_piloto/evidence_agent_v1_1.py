"""Local evidence-verification prototype for the Cabo Verde Stage 0 pilot.

Reads development data only, requests one Qwen3:4b decision via local Ollama,
executes a narrowly scoped read-only PDF reinspection, and logs the outcome.
"""

import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pymupdf

ROOT = Path(__file__).resolve().parent
INPUT_CSV = ROOT / "baseline_v2_results.csv"
LOG_FILE = ROOT / "agent_v1_decision_log.jsonl"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3:4b"
ALLOWED_ACTIONS = {"REINSPECT_SOURCE", "COMPARE_VERSION", "REQUEST_HUMAN_REVIEW"}


def choose_action(record):
    prompt = (
        "You are a cautious public-policy evidence verification assistant. "
        "Choose exactly one next action for this flagged record: "
        "REINSPECT_SOURCE, COMPARE_VERSION, or REQUEST_HUMAN_REVIEW. "
        "Default to REINSPECT_SOURCE to check a discrepancy against the original PDF. "
        "You have not seen the PDF. Do not claim to have accessed any document. "
        "Never change published figures. Avoid unsupported explanations such as rounding of employee counts. "
        "Return only a JSON object with keys action and rationale. "
        "Rationale must be a short English sentence.\n"
        f"Record: {json.dumps(record, ensure_ascii=False)}"
    )
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": {"type": "object", "properties": {"action": {"type": "string", "enum": ["REINSPECT_SOURCE", "COMPARE_VERSION", "REQUEST_HUMAN_REVIEW"]}, "rationale": {"type": "string"}}, "required": ["action", "rationale"]},
        "think": False,
        "options": {"temperature": 0, "num_predict": 400},
    }).encode("utf-8")
    req = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    with urlopen(req, timeout=180) as reply:
        raw = json.load(reply)
    duration_s = round(time.perf_counter() - start, 3)
    response_text = raw.get("response", "")
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as exc:
        preview = response_text[:180].replace("\n", " ")
        raise ValueError(f"MODEL_OUTPUT_INVALID_JSON: {exc}; prefix={preview!r}") from exc
    if not isinstance(result, dict):
        raise ValueError("MODEL_OUTPUT_NOT_AN_OBJECT")
    action = result.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Invalid agent action: {action!r}")
    rationale = str(result.get("rationale", "")).strip()[:350]
    if not rationale:
        raise ValueError("Model returned no rationale")
    return action, rationale, duration_s, raw.get("eval_count"), raw.get("prompt_eval_count")


def reinspect_source(record):
    # Enforce one of the known source filenames and the known development page.
    expected = "2_BALANCO-SOCIAL-CAP-H-ADP.PDF"
    if record["Source Filename"] != expected or int(record["PDF Page"]) != 14:
        return {"tool_status": "BLOCKED_UNSUPPORTED_SOURCE", "evidence": ""}
    source = ROOT.parent / expected
    if not source.is_file():
        return {"tool_status": "SOURCE_FILE_MISSING", "evidence": ""}
    with pymupdf.open(source) as doc:
        page = doc[13]
        matches = [b[4] for b in page.get_text("blocks")
                   if record["Source Institution Label"].strip() in b[4]]
    if len(matches) != 1:
        return {"tool_status": "AMBIGUOUS_OR_MISSING_BLOCK", "match_count": len(matches), "evidence": ""}
    lines = [s.strip() for s in matches[0].splitlines() if s.strip()]
    if len(lines) < 5 or not all(re.fullmatch(r"\d+", x) for x in lines[1:4]):
        return {"tool_status": "UNEXPECTED_BLOCK_FORMAT", "evidence": matches[0].strip()}
    female, male, reported = map(int, lines[1:4])
    extracted = {"female": female, "male": male, "reported_total": reported}
    expected_values = {
        "female": int(record["Female Employees"]),
        "male": int(record["Male Employees"]),
        "reported_total": int(record["Reported Total"]),
    }
    source_matches = extracted == expected_values
    arithmetic_matches = female + male == reported
    status = "SOURCE_CONFIRMED_ARITHMETIC_CONFLICT" if source_matches and not arithmetic_matches else (
        "SOURCE_CONFIRMED" if source_matches else "EXTRACTION_MISMATCH")
    return {
        "tool_status": status,
        "pdf_page": 14,
        "extracted_values": extracted,
        "calculated_total": female + male,
        "evidence": " | ".join(lines[:5]),
    }


def main():
    if not INPUT_CSV.is_file():
        raise SystemExit("Missing baseline_v2_results.csv in the current project folder")
    with INPUT_CSV.open(newline="", encoding="utf-8-sig") as f:
        records = list(csv.DictReader(f))
    flagged = [r for r in records if r.get("Arithmetic Status") == "REVIEW"]
    if len(flagged) != 1:
        raise SystemExit(f"Expected exactly one known development REVIEW record; found {len(flagged)}")
    record = flagged[0]
    # This is a pilot on the already-seen development case, not a held-out test.
    try:
        action, rationale, seconds, output_tokens, input_tokens = choose_action(record)
        if action == "REINSPECT_SOURCE":
            verification = reinspect_source(record)
        else:
            # Do not silently carry out alternatives the prototype has not implemented.
            verification = {"tool_status": "ACTION_NOT_IMPLEMENTED", "evidence": ""}
        error = None
    except (ValueError, KeyError, HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        action, rationale, seconds, output_tokens, input_tokens = "REQUEST_HUMAN_REVIEW", "Agent response or local request failed", None, None, None
        verification = {"tool_status": "AGENT_ERROR", "evidence": ""}
        error = str(exc)[:300]
    log = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "test_phase": "DEVELOPMENT_ONLY",
        "institution": record["Institution"],
        "source_filename": record["Source Filename"],
        "reference_year": record["Reference Year"],
        "pdf_page": record["PDF Page"],
        "model": MODEL,
        "action": action,
        "rationale": rationale,
        "verification": verification,
        "human_review_status": "PENDING",
        "duration_seconds": seconds,
        "prompt_tokens": input_tokens,
        "output_tokens": output_tokens,
        "error": error,
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")
    print("Phase: DEVELOPMENT_ONLY")
    print("Institution:", log["institution"])
    print("Agent action:", action)
    print("Rationale:", rationale)
    print("Tool result:", verification["tool_status"])
    print("Human review: PENDING")
    print("Decision log:", LOG_FILE.name)
    if error:
        print("Error:", error)


if __name__ == "__main__":
    main()
