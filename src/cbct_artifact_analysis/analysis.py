"""Aggregate audit and reproducibility analyses."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.stats.multicomp import pairwise_tukeyhsd

from cbct_artifact_analysis.io import WorkbookData
from cbct_artifact_analysis.study import (
    MANUSCRIPT_CONTROL_P,
    MANUSCRIPT_MATCHED_P,
    MANUSCRIPT_SCAN_MEANS,
    MATCHED_PAIRS,
    MATCHED_SITE_PAIRS,
    SCAN_METADATA,
    SITE_ANATOMY,
    TRAY_PAIR,
    TRAY_SITE_PAIR,
)


@dataclass(frozen=True)
class AuditResults:
    quality_summary: pd.DataFrame
    experimental_design: pd.DataFrame
    site_descriptive_statistics: pd.DataFrame
    zero_by_scan_site_trial: pd.DataFrame
    matched_comparisons: pd.DataFrame
    scan_block_summary: pd.DataFrame
    scan_overall_summary: pd.DataFrame
    manuscript_reproduction: pd.DataFrame
    control_tukey_reproduction: pd.DataFrame
    matched_pair_sensitivity: pd.DataFrame
    matched_p_reproduction: pd.DataFrame
    long: pd.DataFrame
    profile: object


def _tukey_table(values: pd.Series, groups: pd.Series) -> pd.DataFrame:
    result = pairwise_tukeyhsd(endog=values.to_numpy(), groups=groups.to_numpy())
    table = pd.DataFrame(result._results_table.data[1:], columns=result._results_table.data[0])
    table = table.rename(columns={"p-adj": "p_adjusted"})
    for column in ["meandiff", "p_adjusted", "lower", "upper"]:
        table[column] = pd.to_numeric(table[column])
    return table


def _quality_summary(data: WorkbookData) -> pd.DataFrame:
    values = data.long["value"]
    rows = [
        ("Worksheets", 1, "One worksheet expected"),
        (
            "Worksheet extent",
            f"{data.profile.worksheet_rows} × {data.profile.worksheet_columns}",
            "Includes notes/blank padding",
        ),
        ("Data rows / implant sites", len(data.sites), "Expected 18"),
        ("Scans", data.long["scan_id"].nunique(), "Expected A–J"),
        ("Numeric measurements", len(values), "18 sites × 3 trials × 24 cells"),
        ("Missing/non-numeric values", int(values.isna().sum()), "Validated before analysis"),
        ("Zero values", int(values.eq(0).sum()), f"{values.eq(0).mean():.1%} of numeric cells"),
        ("Negative values", int(values.lt(0).sum()), "None expected in current workbook"),
        ("Minimum", f"{values.min():.3f}", "Descriptive only"),
        ("Maximum", f"{values.max():.3f}", "Descriptive only"),
        (
            "Duplicate site codes",
            int(data.sites["site_code"].duplicated().sum()),
            "Site codes should be unique",
        ),
        ("Merged ranges", data.profile.merged_ranges, "Scan labels span multi-site rows"),
        ("Formula cells", data.profile.formulas, "Workbook contains values, not calculations"),
        ("Comments", data.profile.comments, "No embedded data notes"),
        (
            "Tables/charts",
            f"{data.profile.tables}/{data.profile.charts}",
            "No structured Excel table or chart",
        ),
        (
            "Non-empty note rows after data",
            data.profile.note_rows,
            "Free-text requested comparisons",
        ),
    ]
    return pd.DataFrame(rows, columns=["check", "result", "interpretation"])


def _experimental_design() -> pd.DataFrame:
    rows = []
    for scan_id, metadata in SCAN_METADATA.items():
        rows.append(
            {
                "scan": scan_id,
                "implant_number": metadata.implant_count,
                "anatomical_site": metadata.anatomical_site,
                "alginate": "Yes" if metadata.alginate else "No",
                "tray_status": metadata.tray_status,
                "design_note": metadata.description,
            }
        )
    return pd.DataFrame(rows)


def _site_descriptive_statistics(long: pd.DataFrame) -> pd.DataFrame:
    grouped = long.groupby(["scan_id", "site_code"], sort=False)["value"]
    summary = grouped.agg(
        n="size",
        mean="mean",
        sd="std",
        median="median",
        q1=lambda values: values.quantile(0.25),
        q3=lambda values: values.quantile(0.75),
        minimum="min",
        maximum="max",
    ).reset_index()
    summary["iqr"] = summary["q3"] - summary["q1"]
    summary["zero_count"] = grouped.apply(
        lambda values: int(values.eq(0).sum()), include_groups=False
    ).to_numpy()
    summary["zero_percent"] = 100 * summary["zero_count"] / summary["n"]
    summary.insert(2, "anatomical_site", summary["site_code"].map(SITE_ANATOMY))
    return summary[
        [
            "scan_id",
            "site_code",
            "anatomical_site",
            "n",
            "mean",
            "sd",
            "median",
            "q1",
            "q3",
            "iqr",
            "minimum",
            "maximum",
            "zero_count",
            "zero_percent",
        ]
    ]


def _zero_by_scan_site_trial(long: pd.DataFrame) -> pd.DataFrame:
    grouped = long.groupby(["scan_id", "site_code", "block"], sort=False)["value"]
    result = grouped.agg(
        measurement_count="size",
        zero_count=lambda values: int(values.eq(0).sum()),
    ).reset_index()
    result = result.rename(columns={"block": "trial"})
    result["zero_percent"] = 100 * result["zero_count"] / result["measurement_count"]
    result.insert(2, "anatomical_site", result["site_code"].map(SITE_ANATOMY))
    return result


def _matched_site_comparisons(long: pd.DataFrame) -> pd.DataFrame:
    site_overall = long.groupby(["scan_id", "site_code"], sort=False)["value"].agg(
        n="size", mean="mean", median="median"
    )
    site_trial = long.groupby(["scan_id", "site_code", "block"], sort=False)["value"].mean()
    rows = []
    pairs = [(*pair, "Alginate vs no alginate") for pair in MATCHED_SITE_PAIRS] + [
        (*TRAY_SITE_PAIR, "Tray sensitivity; both scans labelled alginate")
    ]
    for comparison, first_site, second_site, anatomical_site, comparison_type in pairs:
        first_scan, second_scan = comparison.split("-")
        first = site_overall.loc[(first_scan, first_site)]
        second = site_overall.loc[(second_scan, second_site)]
        trial_differences = [
            site_trial.loc[(second_scan, second_site, trial)]
            - site_trial.loc[(first_scan, first_site, trial)]
            for trial in (1, 2, 3)
        ]
        rows.append(
            {
                "comparison": comparison,
                "comparison_type": comparison_type,
                "anatomical_site": anatomical_site,
                "first_scan": first_scan,
                "first_condition": SCAN_METADATA[first_scan].condition,
                "first_site_code": first_site,
                "first_n": int(first["n"]),
                "first_mean": float(first["mean"]),
                "first_median": float(first["median"]),
                "second_scan": second_scan,
                "second_condition": SCAN_METADATA[second_scan].condition,
                "second_site_code": second_site,
                "second_n": int(second["n"]),
                "second_mean": float(second["mean"]),
                "second_median": float(second["median"]),
                "difference_second_minus_first": float(second["mean"] - first["mean"]),
                "trial_difference_min": float(min(trial_differences)),
                "trial_difference_max": float(max(trial_differences)),
                "same_direction_all_trials": (
                    all(value > 0 for value in trial_differences)
                    or all(value < 0 for value in trial_differences)
                ),
            }
        )
    return pd.DataFrame(rows)


def _summaries(long: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    grouped = long.groupby(["scan_id", "block"], sort=True)["value"]
    scan_block = grouped.agg(
        n="size", mean="mean", median="median", sd="std", minimum="min", maximum="max"
    ).reset_index()
    zeros = grouped.apply(lambda values: int(values.eq(0).sum()), include_groups=False)
    scan_block["zero_count"] = zeros.to_numpy()
    scan_block["zero_percent"] = 100 * scan_block["zero_count"] / scan_block["n"]
    scan_block["condition"] = scan_block["scan_id"].map(
        {scan_id: metadata.condition for scan_id, metadata in SCAN_METADATA.items()}
    )

    overall_grouped = long.groupby("scan_id", sort=True)["value"]
    overall = overall_grouped.agg(
        n="size", mean="mean", median="median", sd="std", minimum="min", maximum="max"
    ).reset_index()
    overall["zero_count"] = overall_grouped.apply(
        lambda values: int(values.eq(0).sum()), include_groups=False
    ).to_numpy()
    overall["zero_percent"] = 100 * overall["zero_count"] / overall["n"]
    overall["condition"] = overall["scan_id"].map(
        {scan_id: metadata.condition for scan_id, metadata in SCAN_METADATA.items()}
    )
    return scan_block, overall


def _manuscript_reproduction(scan_block: pd.DataFrame) -> pd.DataFrame:
    block_one = scan_block.loc[scan_block["block"].eq(1), ["scan_id", "mean"]].copy()
    block_one = block_one.rename(columns={"mean": "workbook_block_1_mean"})
    block_one["manuscript_mean"] = block_one["scan_id"].map(MANUSCRIPT_SCAN_MEANS)
    block_one["difference"] = block_one["workbook_block_1_mean"] - block_one["manuscript_mean"]
    block_one["reproduces_at_2dp"] = (
        block_one["workbook_block_1_mean"].round(2) == block_one["manuscript_mean"]
    )
    return block_one[
        [
            "scan_id",
            "manuscript_mean",
            "workbook_block_1_mean",
            "difference",
            "reproduces_at_2dp",
        ]
    ]


def _control_tukey_reproduction(long: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    block_one = long.loc[long["block"].eq(1)]
    full_tukey = _tukey_table(block_one["value"], block_one["scan_id"])
    control = full_tukey.loc[full_tukey["group1"].eq("A")].copy()
    control["comparison"] = "A-" + control["group2"].astype(str)
    control["manuscript_p"] = control["group2"].map(MANUSCRIPT_CONTROL_P)
    control["reproduces_at_3dp"] = control["p_adjusted"].round(3) == control["manuscript_p"]
    columns = [
        "comparison",
        "meandiff",
        "manuscript_p",
        "p_adjusted",
        "lower",
        "upper",
        "reject",
        "reproduces_at_3dp",
    ]
    return control[columns], full_tukey


def _matched_pair_sensitivity(scan_block: pd.DataFrame) -> pd.DataFrame:
    means = scan_block.pivot(index="scan_id", columns="block", values="mean")
    rows: list[dict[str, object]] = []
    for comparison, (without_scan, with_scan, scenario) in {
        **MATCHED_PAIRS,
        **TRAY_PAIR,
    }.items():
        for block in means.columns:
            rows.append(
                {
                    "comparison": comparison,
                    "scenario": scenario,
                    "block": int(block),
                    "first_scan_mean": means.loc[without_scan, block],
                    "second_scan_mean": means.loc[with_scan, block],
                    "difference_second_minus_first": (
                        means.loc[with_scan, block] - means.loc[without_scan, block]
                    ),
                }
            )
    return pd.DataFrame(rows)


def _matched_p_reproduction(full_tukey: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for comparison, manuscript_p in MANUSCRIPT_MATCHED_P.items():
        first, second = comparison.split("-")
        match = full_tukey.loc[
            full_tukey["group1"].eq(first) & full_tukey["group2"].eq(second)
        ].iloc[0]
        rows.append(
            {
                "comparison": comparison,
                "manuscript_p": manuscript_p,
                "ten_group_tukey_p": float(match["p_adjusted"]),
                "difference": float(match["p_adjusted"]) - manuscript_p,
                "reproduces_at_3dp": round(float(match["p_adjusted"]), 3) == manuscript_p,
            }
        )
    return pd.DataFrame(rows)


def run_audit(data: WorkbookData) -> AuditResults:
    """Run aggregate checks; the returned long frame remains memory-only."""

    scan_block, overall = _summaries(data.long)
    control_tukey, full_tukey = _control_tukey_reproduction(data.long)
    return AuditResults(
        quality_summary=_quality_summary(data),
        experimental_design=_experimental_design(),
        site_descriptive_statistics=_site_descriptive_statistics(data.long),
        zero_by_scan_site_trial=_zero_by_scan_site_trial(data.long),
        matched_comparisons=_matched_site_comparisons(data.long),
        scan_block_summary=scan_block,
        scan_overall_summary=overall,
        manuscript_reproduction=_manuscript_reproduction(scan_block),
        control_tukey_reproduction=control_tukey,
        matched_pair_sensitivity=_matched_pair_sensitivity(scan_block),
        matched_p_reproduction=_matched_p_reproduction(full_tukey),
        long=data.long,
        profile=data.profile,
    )


def rounded_for_export(frame: pd.DataFrame, digits: int = 4) -> pd.DataFrame:
    """Round numeric aggregate columns without changing boolean/integer columns."""

    output = frame.copy()
    float_columns = output.select_dtypes(include=[np.floating]).columns
    output[float_columns] = output[float_columns].round(digits)
    return output
