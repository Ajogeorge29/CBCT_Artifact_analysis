"""Exploratory Regression Tsetlin Machine feasibility analysis.

The private row-level measurements stay in memory. Only grouped validation metrics, aggregate
clause summaries, and a comparison figure are written to disk.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from cbct_artifact_analysis.analysis import rounded_for_export
from cbct_artifact_analysis.study import SCAN_METADATA, SITE_ANATOMY

CONFIGURATION_GROUPS = {
    "A": "control_no_implant",
    "B": "posterior_one_implant",
    "C": "posterior_one_implant",
    "D": "posterior_one_implant",
    "E": "opposing_arches_two_implants",
    "F": "opposing_arches_two_implants",
    "G": "same_jaw_two_implants",
    "H": "same_jaw_two_implants",
    "I": "three_implants",
    "J": "three_implants",
}

GROUP_ORDER = [
    "control_no_implant",
    "posterior_one_implant",
    "opposing_arches_two_implants",
    "same_jaw_two_implants",
    "three_implants",
]

FEATURE_SETS = {
    "confirmed_design": False,
    "design_plus_provisional_position": True,
}

RTM_PARAMETERS = {
    "number_of_clauses": 200,
    "T": 1000,
    "s": 2.75,
    "weighted_clauses": True,
    "max_included_literals": 6,
    "epochs": 50,
}

MIN_CLAUSE_SUPPORT = 24


@dataclass(frozen=True)
class FeasibilityResults:
    model_summary: pd.DataFrame
    fold_metrics: pd.DataFrame
    clauses: pd.DataFrame
    recommendation: str
    retain_in_manuscript: bool
    library_version: str
    report_path: Path
    figure_path: Path


def _prepare_model_frame(long: pd.DataFrame) -> pd.DataFrame:
    frame = long[
        ["scan_id", "site_code", "block", "measurement", "value", "alginate", "implant_count"]
    ].copy()
    frame = frame.rename(
        columns={"block": "trial", "measurement": "measurement_position", "value": "target"}
    )
    frame["anatomical_site"] = frame["site_code"].map(SITE_ANATOMY)
    frame["tray_status"] = frame["scan_id"].map(
        {scan_id: metadata.tray_status for scan_id, metadata in SCAN_METADATA.items()}
    )
    frame["configuration_group"] = frame["scan_id"].map(CONFIGURATION_GROUPS)
    required = ["anatomical_site", "tray_status", "configuration_group"]
    if frame[required].isna().any().any():
        raise ValueError("Model metadata are incomplete for one or more private workbook rows.")
    return frame


def _binary_features(
    frame: pd.DataFrame, *, include_position: bool
) -> tuple[np.ndarray, list[str]]:
    columns: list[np.ndarray] = []
    names: list[str] = []

    def add(name: str, values: pd.Series | np.ndarray) -> None:
        names.append(name)
        columns.append(np.asarray(values, dtype=np.uint32))

    add("alginate=yes", frame["alginate"])
    for threshold in (1, 2, 3):
        add(f"implant_count>={threshold}", frame["implant_count"].ge(threshold))
    for category in sorted(set(SITE_ANATOMY.values())):
        add(f"anatomical_site={category}", frame["anatomical_site"].eq(category))
    tray_categories = sorted({metadata.tray_status for metadata in SCAN_METADATA.values()})
    for category in tray_categories:
        add(f"tray_status={category}", frame["tray_status"].eq(category))
    for trial in (1, 2, 3):
        add(f"trial={trial}", frame["trial"].eq(trial))
    if include_position:
        for position in range(1, 25):
            add(
                f"provisional_measurement_position={position}",
                frame["measurement_position"].eq(position),
            )

    return np.column_stack(columns).astype(np.uint32), names


def _rule_predictions(
    train: pd.DataFrame, test: pd.DataFrame, *, include_position: bool
) -> np.ndarray:
    """Predict from progressively broader training-fold means."""

    exact = ["alginate", "implant_count", "anatomical_site", "tray_status", "trial"]
    if include_position:
        exact.append("measurement_position")
    hierarchies = [
        exact,
        ["alginate", "anatomical_site", "tray_status", "trial"],
        ["alginate", "anatomical_site", "tray_status"],
        ["alginate", "anatomical_site"],
        ["anatomical_site"],
    ]
    predictions = np.full(len(test), np.nan, dtype=float)
    for keys in hierarchies:
        lookup = train.groupby(keys, observed=True)["target"].mean().to_dict()
        for row_index, row in enumerate(test[keys].itertuples(index=False, name=None)):
            if np.isnan(predictions[row_index]) and row in lookup:
                predictions[row_index] = float(lookup[row])
    predictions[np.isnan(predictions)] = float(train["target"].mean())
    return predictions


def _load_rtm_class():
    try:
        from pyTsetlinMachine.tm import RegressionTsetlinMachine
    except (ImportError, OSError) as error:
        raise RuntimeError(
            "pyTsetlinMachine 0.6.6 is unavailable. Use scripts/run_rtm_feasibility.ps1 "
            "to run the pinned Linux container."
        ) from error
    return RegressionTsetlinMachine


def _new_rtm(rtm_class):
    return rtm_class(
        RTM_PARAMETERS["number_of_clauses"],
        RTM_PARAMETERS["T"],
        RTM_PARAMETERS["s"],
        weighted_clauses=RTM_PARAMETERS["weighted_clauses"],
        max_included_literals=RTM_PARAMETERS["max_included_literals"],
    )


def _metric_row(
    *,
    model: str,
    feature_set: str,
    held_out_group: str,
    held_out_scans: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict[str, object]:
    return {
        "model": model,
        "feature_set": feature_set,
        "held_out_configuration": held_out_group,
        "held_out_scans": held_out_scans,
        "n_test_measurements": len(y_true),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
    }


def _decode_clauses(
    model,
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    feature_set: str,
) -> pd.DataFrame:
    weights, states = model.get_state()
    number_of_input_features = X.shape[1]
    number_of_literals = number_of_input_features * 2
    chunks = (number_of_literals - 1) // 32 + 1
    state_bits = model.number_of_state_bits
    rows: list[dict[str, object]] = []

    for clause_id in range(model.number_of_clauses):
        literal_indexes: list[int] = []
        for literal in range(number_of_literals):
            chunk = literal // 32
            bit = literal % 32
            position = clause_id * chunks * state_bits + chunk * state_bits + state_bits - 1
            if int(states[position]) & (1 << bit):
                literal_indexes.append(literal)
        if not literal_indexes:
            continue

        active = np.ones(len(X), dtype=bool)
        literal_labels: list[str] = []
        for literal in literal_indexes:
            if literal < number_of_input_features:
                active &= X[:, literal].astype(bool)
                literal_labels.append(feature_names[literal])
            else:
                feature_index = literal - number_of_input_features
                active &= ~X[:, feature_index].astype(bool)
                literal_labels.append(f"NOT {feature_names[feature_index]}")
        active_count = int(active.sum())
        if active_count < MIN_CLAUSE_SUPPORT or len(X) - active_count < MIN_CLAUSE_SUPPORT:
            continue
        mean_active = float(np.mean(y[active]))
        mean_inactive = float(np.mean(y[~active]))
        difference = mean_active - mean_inactive
        rows.append(
            {
                "feature_set": feature_set,
                "clause_id": clause_id,
                "clause_weight": int(weights[clause_id]),
                "literal_count": len(literal_indexes),
                "support_count": active_count,
                "support_percent": 100 * active_count / len(X),
                "mean_intensity_when_true": mean_active,
                "mean_intensity_when_false": mean_inactive,
                "observed_difference_true_minus_false": difference,
                "observed_association": "higher" if difference > 0 else "lower",
                "clause": " AND ".join(literal_labels),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "feature_set",
                "clause_id",
                "clause_weight",
                "literal_count",
                "support_count",
                "support_percent",
                "mean_intensity_when_true",
                "mean_intensity_when_false",
                "observed_difference_true_minus_false",
                "observed_association",
                "clause",
                "duplicate_clause_count",
            ]
        )
    clauses = pd.DataFrame(rows)
    clauses["absolute_observed_difference"] = clauses["observed_difference_true_minus_false"].abs()
    clauses = clauses.sort_values(
        ["clause_weight", "absolute_observed_difference"], ascending=[False, False]
    )
    clauses["duplicate_clause_count"] = clauses.groupby("clause")["clause"].transform("size")
    clauses = clauses.drop_duplicates("clause").head(15)
    return clauses.drop(columns="absolute_observed_difference").reset_index(drop=True)


def _summarize_models(
    fold_metrics: pd.DataFrame,
    pooled: dict[tuple[str, str], tuple[list[np.ndarray], list[np.ndarray]]],
) -> pd.DataFrame:
    rows = []
    for (model, feature_set), (truth_parts, prediction_parts) in pooled.items():
        truth = np.concatenate(truth_parts)
        prediction = np.concatenate(prediction_parts)
        subset = fold_metrics.loc[
            fold_metrics["model"].eq(model) & fold_metrics["feature_set"].eq(feature_set)
        ]
        rows.append(
            {
                "model": model,
                "feature_set": feature_set,
                "validation": "5-fold leave-one-scan-configuration-out",
                "n_measurements": len(truth),
                "n_configuration_folds": len(subset),
                "pooled_mae": float(mean_absolute_error(truth, prediction)),
                "pooled_rmse": float(root_mean_squared_error(truth, prediction)),
                "macro_fold_mae": float(subset["mae"].mean()),
                "macro_fold_rmse": float(subset["rmse"].mean()),
            }
        )
    order = {"Rule mean": 0, "Linear regression": 1, "Regression Tsetlin Machine": 2}
    output = pd.DataFrame(rows)
    output["_order"] = output["model"].map(order)
    return (
        output.sort_values(["feature_set", "_order"]).drop(columns="_order").reset_index(drop=True)
    )


def _retention_decision(model_summary: pd.DataFrame, clauses: pd.DataFrame) -> tuple[bool, str]:
    design = model_summary.loc[model_summary["feature_set"].eq("confirmed_design")].set_index(
        "model"
    )
    rtm = design.loc["Regression Tsetlin Machine"]
    comparators = design.loc[["Rule mean", "Linear regression"]]
    beats_both = bool(
        (rtm["pooled_mae"] <= 0.95 * comparators["pooled_mae"]).all()
        and (rtm["pooled_rmse"] <= 0.95 * comparators["pooled_rmse"]).all()
    )
    interpretable = clauses.loc[
        clauses["feature_set"].eq("confirmed_design")
        & clauses["support_percent"].between(5, 95)
        & clauses["literal_count"].between(1, 4)
    ]
    if beats_both and len(interpretable) >= 3:
        return (
            True,
            "The pre-specified design-only RTM cleared the exploratory performance rule and "
            "yielded supported short clauses. It may be retained only as a clearly labelled "
            "secondary feasibility analysis, not as a validated predictive system.",
        )
    return (
        False,
        "Do not retain the RTM as a manuscript result. The design-only RTM had pooled "
        f"MAE/RMSE {rtm['pooled_mae']:.1f}/{rtm['pooled_rmse']:.1f}, versus "
        f"{design.loc['Linear regression', 'pooled_mae']:.1f}/"
        f"{design.loc['Linear regression', 'pooled_rmse']:.1f} for linear regression and "
        f"{design.loc['Rule mean', 'pooled_mae']:.1f}/"
        f"{design.loc['Rule mean', 'pooled_rmse']:.1f} for the rule baseline. Its supported "
        "clauses mostly restate condition, tray, anatomy, and trial patterns already visible in "
        "the descriptive summaries. Keep it as a reproducible feasibility appendix or "
        "future-work note.",
    )


def _markdown_table(frame: pd.DataFrame) -> str:
    display = rounded_for_export(frame)
    headers = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in display.itertuples(index=False, name=None):
        cells = [str(value).replace("|", "\\|") for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _write_figure(model_summary: pd.DataFrame, path: Path) -> None:
    labels = [
        f"{row.model}\n{row.feature_set.replace('_', ' ')}"
        for row in model_summary.itertuples(index=False)
    ]
    colors = {
        "Rule mean": "#7a8797",
        "Linear regression": "#2b6f97",
        "Regression Tsetlin Machine": "#c75b39",
    }
    bar_colors = [colors[model] for model in model_summary["model"]]
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    for axis, metric, title in zip(
        axes, ("pooled_mae", "pooled_rmse"), ("Pooled MAE", "Pooled RMSE"), strict=True
    ):
        axis.barh(labels, model_summary[metric], color=bar_colors)
        axis.set_xlabel("Gray-value units (lower is better)")
        axis.set_title(title)
        axis.grid(axis="x", alpha=0.25)
        axis.invert_yaxis()
    figure.suptitle("Grouped feasibility validation by held-out scan configuration", weight="bold")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _write_report(
    *,
    model_summary: pd.DataFrame,
    fold_metrics: pd.DataFrame,
    clauses: pd.DataFrame,
    recommendation: str,
    retain: bool,
    library_version: str,
    output_path: Path,
) -> None:
    clause_display = clauses[
        [
            "feature_set",
            "clause_weight",
            "literal_count",
            "support_percent",
            "observed_difference_true_minus_false",
            "observed_association",
            "clause",
        ]
    ]
    text = f"""# Regression Tsetlin Machine feasibility report

## Decision

**Retain as a manuscript secondary analysis: {"Yes" if retain else "No"}.** {recommendation}

This is an exploratory feasibility experiment, not a validated predictive system. The primary
paired analysis remains the trial-level matched analysis in
`tables/paired_trial_analysis.csv` and the descriptive matched comparisons in Table 3.

## Methods

- Target: recorded CBCT gray value; all zeros were retained.
- Validation: five leave-one-scan-configuration-out folds. B/C/D, E/F, G/H, and I/J are held out
  together as configuration families; Scan A forms the control fold. No scan identifier is a model
  feature.
- Confirmed-design features: alginate status, implant-count thresholds, anatomical site, tray
  status, and trial.
- Position sensitivity: adds the spreadsheet column index 1–24. This is explicitly **not** a
  validated radius/direction label and cannot support a clinical spatial interpretation.
- Encoding: predictors are represented as explicit Boolean one-hot or threshold features instead
  of opaque continuous bins, so extracted clause literals remain readable.
- Comparators: ordinary linear regression on the same binary design matrix and a training-fold-only
  hierarchical mean rule.
- Retention rule: before inspecting the results, require the confirmed-design RTM to improve both
  pooled MAE and RMSE by at least 5% over both baselines and provide at least three supported clauses
  with no more than four literals.
- RTM: `pyTsetlinMachine` {library_version}; {RTM_PARAMETERS["number_of_clauses"]} clauses,
  `T={RTM_PARAMETERS["T"]}`, `s={RTM_PARAMETERS["s"]}`, weighted clauses,
  `max_included_literals={RTM_PARAMETERS["max_included_literals"]}`, and
  {RTM_PARAMETERS["epochs"]} epochs. Hyperparameters were fixed for this small feasibility run, not
  optimized against the validation folds.

The folds separate scan configurations, but the 1,296 target values are still repeated technical
measurements from only five configuration families. MAE and RMSE are descriptive out-of-group
errors, not precision estimates or evidence of clinical generalizability.

## Aggregate model comparison

{_markdown_table(model_summary)}

![Grouped model comparison](figures/rtm_model_comparison.png)

## Per-configuration results

{_markdown_table(fold_metrics)}

## Clause audit

Each displayed clause is a conjunction. RTM regression clauses contribute non-negative votes when
true; “higher” or “lower” below is the observed mean target difference for rows where the clause was
true versus false, not a causal effect. Duplicate logical clauses are collapsed, and clauses with
fewer than {MIN_CLAUSE_SUPPORT} true or false observations are omitted to prevent narrow aggregate
disclosures.

{_markdown_table(clause_display)}

Clause interpretation is provisional because scan condition, anatomy, implant count, tray status,
and alginate are partially confounded by design. Any clause containing
`provisional_measurement_position` must remain outside the manuscript until the 24-column mapping is
validated.

## Literature and implementation note

[Granmo (2018)](https://arxiv.org/abs/1804.01508) is the foundational Tsetlin Machine paper. The
regression extension is described separately by
[Abeyrathna et al. (2019)](https://arxiv.org/abs/1905.04206). The experiment uses the maintainers'
[pyTsetlinMachine implementation](https://github.com/cair/pyTsetlinMachine). Its compiled extension
is run in a pinned Linux container because the legacy package does not publish a compatible Windows
wheel for the project's Python environment.

## Privacy

The container image is built before any private-data mount. The analysis container runs without
network access, mounts the workbook read-only, and exports aggregate metrics and clause summaries
only. It does not write row-level observations or predictions.
"""
    output_path.write_text(text, encoding="utf-8")


def run_rtm_feasibility(long: pd.DataFrame, output_dir: str | Path) -> FeasibilityResults:
    """Run grouped RTM feasibility validation and write aggregate-only outputs."""

    rtm_class = _load_rtm_class()
    library_version = version("pyTsetlinMachine")
    frame = _prepare_model_frame(long)
    y = frame["target"].to_numpy(dtype=float)
    fold_rows: list[dict[str, object]] = []
    pooled: dict[tuple[str, str], tuple[list[np.ndarray], list[np.ndarray]]] = {}
    clause_frames: list[pd.DataFrame] = []

    for feature_set, include_position in FEATURE_SETS.items():
        X, feature_names = _binary_features(frame, include_position=include_position)
        for held_out_group in GROUP_ORDER:
            test_mask = frame["configuration_group"].eq(held_out_group).to_numpy()
            train_mask = ~test_mask
            train = frame.loc[train_mask]
            test = frame.loc[test_mask]
            y_train = y[train_mask]
            y_test = y[test_mask]
            held_out_scans = ",".join(sorted(test["scan_id"].unique()))

            predictions = {
                "Rule mean": _rule_predictions(train, test, include_position=include_position),
                "Linear regression": LinearRegression()
                .fit(X[train_mask], y_train)
                .predict(X[test_mask]),
            }
            rtm = _new_rtm(rtm_class)
            rtm.fit(X[train_mask], y_train, epochs=RTM_PARAMETERS["epochs"])
            predictions["Regression Tsetlin Machine"] = rtm.predict(X[test_mask])

            for model_name, prediction in predictions.items():
                fold_rows.append(
                    _metric_row(
                        model=model_name,
                        feature_set=feature_set,
                        held_out_group=held_out_group,
                        held_out_scans=held_out_scans,
                        y_true=y_test,
                        y_pred=np.asarray(prediction, dtype=float),
                    )
                )
                truth_parts, prediction_parts = pooled.setdefault(
                    (model_name, feature_set), ([], [])
                )
                truth_parts.append(y_test)
                prediction_parts.append(np.asarray(prediction, dtype=float))

        final_rtm = _new_rtm(rtm_class)
        final_rtm.fit(X, y, epochs=RTM_PARAMETERS["epochs"])
        clause_frames.append(
            _decode_clauses(final_rtm, X, y, feature_names, feature_set=feature_set)
        )

    fold_metrics = pd.DataFrame(fold_rows)
    model_summary = _summarize_models(fold_metrics, pooled)
    clauses = pd.concat(clause_frames, ignore_index=True)
    retain, recommendation = _retention_decision(model_summary, clauses)

    output = Path(output_dir)
    table_dir = output / "tables"
    figure_dir = output / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    rounded_for_export(model_summary).to_csv(table_dir / "rtm_model_summary.csv", index=False)
    rounded_for_export(fold_metrics).to_csv(table_dir / "rtm_fold_metrics.csv", index=False)
    rounded_for_export(clauses).to_csv(table_dir / "rtm_clause_summary.csv", index=False)

    figure_path = figure_dir / "rtm_model_comparison.png"
    _write_figure(model_summary, figure_path)
    report_path = output / "rtm_feasibility_report.md"
    _write_report(
        model_summary=model_summary,
        fold_metrics=fold_metrics,
        clauses=clauses,
        recommendation=recommendation,
        retain=retain,
        library_version=library_version,
        output_path=report_path,
    )
    metadata = {
        "privacy": "Private workbook read-only; aggregate outputs only; no row-level predictions",
        "validation": "5-fold leave-one-scan-configuration-out",
        "configuration_groups": CONFIGURATION_GROUPS,
        "feature_sets": FEATURE_SETS,
        "rtm_library": f"pyTsetlinMachine {library_version}",
        "rtm_parameters": RTM_PARAMETERS,
        "retain_in_manuscript": retain,
    }
    (output / "rtm_run_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return FeasibilityResults(
        model_summary=model_summary,
        fold_metrics=fold_metrics,
        clauses=clauses,
        recommendation=recommendation,
        retain_in_manuscript=retain,
        library_version=library_version,
        report_path=report_path,
        figure_path=figure_path,
    )
