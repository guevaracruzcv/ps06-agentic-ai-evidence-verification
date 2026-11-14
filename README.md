# Agentic AI for Evidence-Based Public Policy Research

**MIT Agentic AI - Term Project (PS06 / Deliverable #2)**
**Author:** Guevara M. Cruz
**Case study:** Cabo Verde public administration workforce statistics, reference year 2015
**Project status:** Completed bounded development proof of concept; independent evaluation not completed

## 1. Project overview

The broader research question is: **Who is positioned to benefit from AI in Cabo Verde's public administration, and who may be left behind?** Answering it credibly requires reliable, sufficiently detailed workforce evidence.

This four-week course project addresses a narrower engineering question: **Can a local AI agent select and execute a controlled verification action on a flagged statistic while preserving source evidence and human oversight?** It does not estimate the employment effects of AI or characterize today's public-sector workforce.

The prototype combines deterministic PDF extraction and arithmetic checking in Python with a locally hosted language model that selects a next verification action. Python executes the permitted tool, and the result is recorded for human review.

**Demonstrated outcome:** In one successful development run, Qwen3:4b selected `REINSPECT_SOURCE` and a Python tool confirmed an arithmetic discrepancy in the original PDF. The reported figure was not changed; the human-review status remained `PENDING`.

## 2. Why the scope changed

The initial PS06 proposal anticipated 20-30 manually checked observations across 2-3 indicators, using the INE ODS 2015-2025 statistical report, an independent gold set, a SQLite evidence ledger, and a comparison of a Python-only baseline with the agentic workflow.

The actual implementation focused on five selected institutional records in **Table 1 of a 2016 public administration social report (data reference year: 2015)**. Updated and consolidated administrative workforce data were not available to this pilot at the level required for a credible contemporary study. The research question about AI and jobs therefore remained a longer-term motivation, not a conclusion of the project.

The sample reduction, source substitution and architectural substitutions were implementation choices. The project's data-access limitation does **not** establish that the original evaluation requirements were satisfied. These differences are reported below.

## 3. Evidence sources and provenance

- **Primary report:** *Balanco Social do Capital Humano da Administracao Publica*, produced in 2016 with reference data for 2015, Cabo Verde's National Directorate of Public Administration (DNAP).
- **Primary file:** `2_BALANCO-SOCIAL-CAP-H-ADP.PDF` (57 pages). The prototype reads **PDF page 14 / printed page 2**, Table 1.
- **Related edition:** `Balanco-Social-Administracao-30-03-2016-3.pdf` (local filename may contain accented characters). Both PDFs concern the same historical report. They must **not** be counted as independent data sources.
- **Development reference:** `table1_source_A_EN.csv`, manually prepared from the report. It was used during development and is **not** an independent held-out gold set.
- **Evaluation planning:** `Evidence_Test_Case_Matrix_V1_EN.xlsx` describes development cases and proposed held-out sections. The existence of this matrix does not mean those evaluation cases were executed.

PDF extracts and computed totals retain their original source filename, PDF page, reference year, institutional label and source-text excerpt. Original source values are preserved even when a check flags them.

## 4. System architecture

```text
Original PDF, Table 1 (2015 data)
           |
           v
Python + PyMuPDF: extract five specified institutional records
           |
           v
Deterministic arithmetic checks + development-reference comparison
           |                                  |
           |                                  +--> baseline_v2_results.csv
           |                                  +--> baseline_v2_comparison.csv
           v
One flagged development record (REVIEW)
           |
           v
Ollama / Qwen3:4b: choose a permitted next action
           |
           v
Python tool: REINSPECT_SOURCE (read-only PDF reinspection)
           |
           v
agent_v1_decision_log.jsonl: action, evidence, outcome, errors
           |
           v
Technical verification: COMPLETED
Source discrepancy: CONFIRMED
Human adjudication: NOT PERFORMED
Logged human-review status: PENDING
```

**Separation of responsibilities:** Python performs extraction, arithmetic and source reinspection; the model selects an action under a constrained prompt and schema. The prompt explicitly favors source reinspection. This is a bounded action-selection demonstration, **not** an open-ended planning agent.

Only `REINSPECT_SOURCE` has an implemented verification tool. If the model chooses another allowed action, the current prototype reports `ACTION_NOT_IMPLEMENTED`. Failures trigger a safe `REQUEST_HUMAN_REVIEW` fallback and are logged as errors, not counted as successful model decisions.

## 5. Implementation files

| File | Purpose |
| --- | --- |
| `02_extracao_piloto/pdf_baseline_v2.py` | Deterministic extraction, arithmetic validation and development-reference comparison. |
| `02_extracao_piloto/evidence_agent_v1_1.py` | Local Qwen action selection, read-only source reinspection and decision logging. |
| `02_extracao_piloto/table1_source_A_EN.csv` | Five-record development reference used by the baseline. |
| `02_extracao_piloto/baseline_v2_results.csv` | Extracted source values, calculated totals, statuses and provenance. |
| `02_extracao_piloto/baseline_v2_comparison.csv` | Field-by-field comparison with the development reference. |
| `02_extracao_piloto/agent_v1_decision_log.jsonl` | Recorded agent events, including the failed and successful development runs. |
| `02_extracao_piloto/Evidence_Test_Case_Matrix_V1_EN.xlsx` | Test-design matrix; held-out cases were not executed. |
| `02_extracao_piloto/Week4_Evidence_SHA256.txt` | Optional local integrity manifest, if retained in the submitted package. |

The current Python code expects the source PDF **one directory above** `02_extracao_piloto/`. A compatible local layout is:

```text
research_project jobs AI/
|-- README.md
|-- 2_BALANCO-SOCIAL-CAP-H-ADP.PDF     # local source; review sharing rights
`-- 02_extracao_piloto/
    |-- pdf_baseline_v2.py
    |-- evidence_agent_v1_1.py
    |-- table1_source_A_EN.csv
    |-- baseline_v2_results.csv
    |-- baseline_v2_comparison.csv
    |-- agent_v1_decision_log.jsonl
    `-- Evidence_Test_Case_Matrix_V1_EN.xlsx
```

This is a **local execution layout**, not a claim that all files have been uploaded to a GitHub repository. Before publication, check the source-document redistribution conditions and remove any unrelated, personal, confidential or internal files.

## 6. Recorded development results

### 6.1 Deterministic baseline

Five selected institutions were successfully parsed. Their extracted fields matched the **development reference** in the seven compared fields for each record (5/5 records). This is not a measured general accuracy rate, because the reference was prepared from the same source and the examples were used during development.

| Institution | Female | Male | Published total | Calculated total | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| Education and Sports | 5,226 | 3,734 | 8,959 | 8,960 | `REVIEW` |
| Internal Administration | 375 | 1,920 | 2,295 | 2,295 | `MATCH` |
| Rural Development | 409 | 1,297 | 1,706 | 1,706 | `MATCH` |
| Health | 1,098 | 591 | 1,689 | 1,689 | `MATCH` |
| Finance and Planning | 480 | 553 | 1,033 | 1,033 | `MATCH` |

For Education and Sports, **5,226 + 3,734 = 8,960**, while the document publishes **8,959**. The calculated difference (`reported - calculated`) is **-1**. The prototype flags the inconsistency without silently correcting the source.

### 6.2 Agent action and tool result

Two events were recorded on **5 November 2026**, and both are labeled `DEVELOPMENT_ONLY`:

1. **Initial attempt:** malformed model JSON caused an `AGENT_ERROR`. The system safely logged `REQUEST_HUMAN_REVIEW` as a fallback, with approval still `PENDING`. This was not successful model-selected tool use.
2. **Successful attempt:** Qwen3:4b selected `REINSPECT_SOURCE`; Python checked the relevant PDF evidence and returned `SOURCE_CONFIRMED_ARITHMETIC_CONFLICT`. Human approval remained `PENDING`.

The logged duration of the successful attempt was **9.406 seconds**, with **317 prompt tokens** and **54 output tokens**. These figures describe **one run**; they do not establish reliability, throughput or a fair comparative speed/cost advantage. No paid remote API call was made during this local test.

### 6.3 Additional contextual check

A separate **prompt-only** development exercise considered missing educational-attainment records reported in Table 4 (PDF page 29). The correct methodological distinction is that an absent or outdated qualification record does **not** mean an employee lacks qualifications. This was a contextual interpretation exercise, **not** an agent tool-execution test.

## 7. Evaluation status and proposal deviations

| Original target | Observed status |
| --- | --- |
| Real public-sector evidence problem | Completed with historical administrative data. |
| 20-30 observations across 2-3 indicators | Scope reduced to five Table 1 development records. |
| Python baseline | Implemented, with CSV results and comparison. |
| Model-selected action followed by a tool | Demonstrated for one bounded source-reinspection case. |
| SQLite evidence ledger | Not implemented; CSV and JSONL used instead. |
| Independent gold set and >=95% exact accuracy | Not evaluated. |
| Full traceability of approved records | Not established; one logged source-specific case, approval pending. |
| Missing/conflict handling on a seeded evaluation set | Not fully evaluated; one conflict flagged and source-verified. |
| Comparative error, time, human effort and costs | Not measured on the same independent test set. |
| Generalization to unseen tables or sections | Not tested. |

Held-out candidates recorded in the matrix include HE-01 (career structure), HE-02 (teachers by educational level) and HE-03 (autonomous-services geographic distribution). They remained **design candidates**: no independent gold set was assembled or approved, and neither the baseline nor agent was run against these held-out cases. The code's document and page restrictions prevent a valid generalization claim.

## 8. Reproduction notes (Windows + Git Bash)

The working prototype was developed on Windows with Git Bash and Python. It requires the original PDF, the development-reference CSV and the `pymupdf` package. Agent execution additionally requires Ollama running locally with model `qwen3:4b` available.

From Git Bash, navigate to the existing local pilot directory (the path below is the author's working layout):

```bash
cd ~/OneDrive/Documentos/1_MITCourses/_AgenticAI2026/"research_project jobs AI"/02_extracao_piloto
```

If needed, install the Python dependency in the intended environment:

```bash
python -m pip install pymupdf
```

To regenerate the deterministic baseline **only if a rerun is desired**:

```bash
python pdf_baseline_v2.py
```

This command reads the parent-directory PDF and `table1_source_A_EN.csv`, and **overwrites** the two baseline output CSVs. It does not use a language model.

To run the agent **only if a new local experiment is intentionally desired**, first make sure Ollama is running and `ollama list` shows `qwen3:4b`, then execute:

```bash
python evidence_agent_v1_1.py
```

This sends a request to the **local** Ollama endpoint (`127.0.0.1:11434`) and **appends a new event** to `agent_v1_decision_log.jsonl`. Model responses and runtimes may vary. **No rerun is required to review the recorded academic evidence**, and earlier failure/success logs should be preserved.

## 9. Safeguards and limitations

- Preserve source values, source identity, page, year and evidence excerpt; never overwrite historical data with a calculated correction.
- Treat all extracted document text as evidence requiring validation, not as authoritative instructions to the model.
- A `PENDING` review state means the discrepancy has **not** been approved or corrected by a human reviewer.
- The two PDF editions are related versions of **one report**, not two independent confirmations.
- The five observations were used in development; no independent accuracy, model superiority or error-rate claims can be made.
- Source reinspection is hard-coded to Table 1, PDF page 14 and the known source filename; a more capable model would not remove these restrictions without code changes.
- Local inference avoided paid API calls in the recorded test, but hardware, energy, maintenance and development costs were not benchmarked.
- This classroom prototype is **not** a government production system and provides no evidence about current employment impacts from AI.

## 10. Lessons learned

1. **System architecture matters as much as model quality.** A stronger model may improve structured responses but cannot automatically fix hard-coded source limits.
2. **The agentic contribution must be observable.** Python already found the numerical discrepancy; the model's added behavior was choosing a permitted action that triggered an implemented verification tool.
3. **Failures are evidence, not successes.** Invalid JSON, fallback decisions and successful tool invocations must be reported separately.
4. **Development evidence is not independent validation.** Accuracy thresholds, time savings and reliability claims require a held-out reference and comparable measurements.
5. **Public-sector evidence requires careful interpretation.** Missing administrative records are not equivalent to missing employee qualifications or capabilities.
6. **Human oversight is a design boundary.** The agent can propose and perform bounded checks but cannot silently approve disputed source values.

## 11. Video demonstration

**Deliverable #2 video:** [Watch the author's OneDrive recording](https://1drv.ms/v/c/a6a91cb71160b1a9/IQCcsmXEhQwnTJTwRcXiPlUMASPiwwHV64kQId-jbDsbfMg?e=kJCmMA)
**Edited duration:** approximately **4 minutes 27 seconds**.
**Format:** high-level updates, introduction, pitch, technology, code, recorded prototype demonstration, risks and next steps.

The demonstration presents the **recorded development run**, not a new live execution. Link access for the intended reviewer should be confirmed before submission; this document does not assert that anonymous playback is enabled.

## 12. Next steps and submission boundary

The academic proof of concept and recorded demonstration are complete within their stated scope. The remaining administrative work is to verify the submission instructions, review the source/document permissions, and package the approved evidence. Feedback may be considered after grading. Broader research into AI exposure, automation and augmentation across public-sector occupations remains a separate future project, dependent on suitable workforce data and an independently validated research design.

**Submission note:** A README, working code and an accessible video link do not on their own prove a formal course submission. Follow the instructor's required repository, deadline and delivery method. No GitHub publication or instructor approval is claimed here.
