"""Command-line entry point for the private-data audit pipeline."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
import numpy
import openpyxl
import pandas
import scipy
import statsmodels

from cbct_artifact_analysis.analysis import rounded_for_export, run_audit
from cbct_artifact_analysis.feasibility import run_rtm_feasibility
from cbct_artifact_analysis.io import WorkbookValidationError, load_master_workbook
from cbct_artifact_analysis.report import write_reports
from cbct_artifact_analysis.visualize import create_figures

DEFAULT_INPUT = Path("data/private/Alginate study master chart.xlsx")
DEFAULT_OUTPUT = Path("reports")


def _write_aggregate_tables(results: object, table_dir: Path) -> list[Path]:
    table_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "table_1_experimental_design.csv": results.experimental_design,
        "table_2_site_descriptive_statistics.csv": results.site_descriptive_statistics,
        "table_3_matched_comparisons.csv": results.matched_comparisons,
        "zero_audit_by_scan_site_trial.csv": results.zero_by_scan_site_trial,
        "quality_summary.csv": results.quality_summary,
        "scan_block_summary.csv": results.scan_block_summary,
        "scan_overall_summary.csv": results.scan_overall_summary,
        "manuscript_reproduction.csv": results.manuscript_reproduction,
        "control_tukey_reproduction.csv": results.control_tukey_reproduction,
        "matched_pair_sensitivity.csv": results.matched_pair_sensitivity,
        "paired_trial_analysis.csv": results.paired_trial_analysis,
        "matched_p_reproduction.csv": results.matched_p_reproduction,
    }
    paths = []
    for filename, frame in tables.items():
        path = table_dir / filename
        rounded_for_export(frame).to_csv(path, index=False)
        paths.append(path)
    return paths


def _write_run_metadata(input_path: Path, output_dir: Path) -> Path:
    # Deliberately excludes an input checksum: publishing a checksum can make a private file easier
    # to identify across systems. A controlled archival run can record it outside this repository.
    metadata = {
        "generated_at_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "input_filename": input_path.name,
        "privacy": "Source workbook excluded; aggregate outputs only",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            "matplotlib": matplotlib.__version__,
            "numpy": numpy.__version__,
            "openpyxl": openpyxl.__version__,
            "pandas": pandas.__version__,
            "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__,
        },
    }
    path = output_dir / "run_metadata.json"
    path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return path


def _run(input_path: Path, output_dir: Path) -> int:
    data = load_master_workbook(input_path)
    results = run_audit(data)
    figures = create_figures(results, output_dir / "figures")
    table_paths = _write_aggregate_tables(results, output_dir / "tables")
    markdown_path, html_path, meeting_path = write_reports(results, figures, output_dir)
    metadata_path = _write_run_metadata(input_path, output_dir)

    print(f"Validated {len(data.sites)} site rows and {len(data.long)} numeric measurements.")
    print(f"Wrote {len(table_paths)} aggregate tables to {output_dir / 'tables'}.")
    print(f"Markdown report: {markdown_path}")
    print(f"HTML report: {html_path}")
    print(f"Meeting summary: {meeting_path}")
    print(f"Run metadata: {metadata_path}")
    print("Privacy check: no row-level table was written.")
    return 0


def _run_rtm(input_path: Path, output_dir: Path) -> int:
    data = load_master_workbook(input_path)
    results = run_rtm_feasibility(data.long, output_dir)
    print(f"Validated {len(data.sites)} site rows before grouped model evaluation.")
    print(f"RTM library: pyTsetlinMachine {results.library_version}")
    print(f"Feasibility report: {results.report_path}")
    print(f"Model comparison figure: {results.figure_path}")
    print(f"Retain in manuscript: {'yes' if results.retain_in_manuscript else 'no'}")
    print("Privacy check: aggregate metrics and clause summaries only; no row-level output.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cbct-audit",
        description="Audit the private CBCT master workbook and create aggregate reports.",
    )
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="Run validation, analysis, and reporting")
    run_parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    run_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    rtm_parser = subparsers.add_parser(
        "rtm-feasibility", help="Run grouped Regression Tsetlin Machine feasibility analysis"
    )
    rtm_parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    rtm_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        args = parser.parse_args(["run"] if argv is None else ["run", *argv])
    try:
        if args.command == "rtm-feasibility":
            return _run_rtm(args.input, args.output_dir)
        return _run(args.input, args.output_dir)
    except (FileNotFoundError, RuntimeError, WorkbookValidationError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
