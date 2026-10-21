# CBCT alginate artifact analysis

Reproducible audit and visualization pipeline for the ex-vivo study **“Evaluating the
Effect of Alginate Impression Material on Metal Artifact Generated in Cone-Beam Computed
Tomography (CBCT) Scans.”**

The project answers three practical questions:

1. Is the private master workbook structurally usable and internally consistent?
2. Can the descriptive values and p-values printed in the manuscripts be reproduced?
3. How sensitive are the conclusions to the workbook's three 24-measurement trial blocks?

## Current audit result

The private workbook contains 18 implant-site rows, 10 scans (A–J), and 1,296 numeric
measurements. Each site has 72 values arranged as three 24-measurement trials. The within-trial
radius/direction order still requires a signed-off data dictionary. The
manuscripts describe 24 values per site—eight points at three radii—and 9 of 10 printed scan
means match **trial 1 only** at two decimals. Scan F is close but not exact: the workbook gives
632.2047 (632.20 at two decimals), while the manuscripts print 632.21.

The Scan A comparison p-values also reproduce as a ten-group Tukey HSD on trial 1. This
identifies the prior calculation, but it raises two issues that must be resolved before
submission:

- trials 2 and 3 account for two-thirds of the workbook's measurements but are absent from the
  reported manuscript calculation;
- point-level PIV measurements are nested within implant sites and scans, so treating them as
  independent replicates may produce pseudoreplication.

The detailed findings, figures, reconciliation tables, limitations, and recommended fixes are in
the [data audit report](reports/data_audit_report.md). The formatted browser version is
`reports/data_audit_report.html`.

The professor-requested deliverables are indexed in
[PROFESSOR_CHECKLIST.md](docs/PROFESSOR_CHECKLIST.md), including three numbered tables, two numbered
figures, revised manuscript copies, and a [one-page meeting summary](reports/meeting_summary.md).

This is a data-quality and reproducibility audit, not a clinical claim. The data currently support
descriptive exploration; confirmatory inference requires a defined experimental unit, documented
column schema, and adequate independent replication.

## Repository layout

```text
.
├── data/
│   ├── README.md                 # private-data handling instructions
│   └── private/                  # ignored; workbook lives here locally
├── docs/
│   ├── source/                   # manuscript and abstract source documents
│   ├── revised/                  # revised-framing manuscript copies
│   ├── ANALYSIS_DECISIONS.md     # traceable assumptions and open decisions
│   ├── PROFESSOR_CHECKLIST.md
│   ├── REVISED_OBJECTIVE_AND_HYPOTHESIS.md
│   ├── STATISTICAL_LIMITATIONS.md
│   └── DATA_DICTIONARY_REQUIRED.md
├── reports/
│   ├── data_audit_report.html    # generated visual report
│   ├── data_audit_report.md      # GitHub-readable report
│   ├── figures/                  # aggregate plots only
│   └── tables/                   # aggregate CSVs only
├── scripts/
│   ├── privacy_guard.py          # blocks raw/private data from Git
│   └── run_analysis.ps1
├── src/cbct_artifact_analysis/   # ingestion, audit, statistics, figures, report
├── tests/                        # synthetic-data tests; no private data required
└── pyproject.toml
```

## Private dataset policy

The workbook must remain at the ignored local path:

```text
data/private/Alginate study master chart.xlsx
```

Protection is layered:

- `.gitignore` excludes Excel and common raw-research formats;
- `scripts/privacy_guard.py` checks staged and tracked files;
- continuous integration runs the privacy guard on every push and pull request;
- the pipeline keeps long-form measurements in memory and writes aggregates only;
- tests use a generated synthetic workbook.

Do not force-add the workbook with `git add -f`. Do not export de-identified-looking row-level
data to another tracked format without a formal disclosure review.

## Quick start

Prerequisites: Python 3.11 or newer and Git.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m cbct_artifact_analysis run
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts/privacy_guard.py --tracked
```

Or, after installing the package:

```powershell
.\scripts\run_analysis.ps1
```

The command validates the workbook before analysis. It fails loudly if sheet count, scan IDs,
site counts, measurement count, or numeric completeness changes.

## Analysis outputs

The pipeline generates these aggregate artifacts:

- scan and trial summary statistics;
- Tables 1–3 requested by the professor and a scan/site/trial zero audit;
- exact reconciliation of manuscript means with workbook trial 1;
- reproduction of the Scan A Tukey HSD table;
- a sensitivity analysis for B–C, E–F, G–H, I–J, and the C–D tray comparison across all trials;
- zero-value and structural quality checks;
- seven publication-oriented figures, including the two numbered professor figures;
- Markdown and HTML audit reports;
- a one-page meeting summary;
- software-version run metadata.

No cleaned row-level CSV is created by design.

## Known limitations

- The three trial blocks are identifiable by position, but the 24 within-trial columns have no names.
  Their mapping to radius, direction, repeat/slice, or observer is unknown.
- Exact zeros are common and lack a documented meaning.
- The workbook contains no qualitative Likert ratings, reader IDs, CBCT identifiers, ROI
  coordinates, or extraction-code provenance.
- Scan conditions vary in implant count and location; Scan A also has no implant.
- The manuscript's E–F, G–H, and I–J p-values are not reproduced by the same Tukey procedure used
  for the Scan A table, and the alternative method is not stated.

Resolve the questions in [DATA_DICTIONARY_REQUIRED.md](docs/DATA_DICTIONARY_REQUIRED.md) before
locking a final statistical analysis plan.

## Quality checks

```powershell
ruff check .
pytest
python scripts/privacy_guard.py --tracked
python scripts/privacy_guard.py --staged
```

The CI workflow runs linting, synthetic-data tests, and the privacy check without requiring access
to the private workbook.
