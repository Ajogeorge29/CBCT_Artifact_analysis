"""Publication-oriented aggregate visualizations."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from cbct_artifact_analysis.analysis import AuditResults

SCAN_ORDER = list("ABCDEFGHIJ")
BLOCK_COLORS = {1: "#1f77b4", 2: "#2ca02c", 3: "#9467bd"}
PAIR_ORDER = ["B-C", "E-F", "G-H", "I-J", "C-D"]


def _style() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "#fbfcfe",
            "axes.titleweight": "bold",
            "axes.titlepad": 12,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.bbox": "tight",
        }
    )


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)


def plot_block_means(results: AuditResults, path: Path) -> None:
    summary = results.scan_block_summary
    fig, axis = plt.subplots(figsize=(11, 5.8))
    for block in (1, 2, 3):
        block_data = summary.loc[summary["block"].eq(block)].set_index("scan_id").loc[SCAN_ORDER]
        axis.plot(
            SCAN_ORDER,
            block_data["mean"],
            marker="o",
            linewidth=2.2,
            markersize=6,
            color=BLOCK_COLORS[block],
            label=f"Trial {block}",
        )
    axis.axvspan(-0.35, 0.35, color="#6c757d", alpha=0.09, label="No-implant control")
    axis.set(title="Mean pixel intensity by scan and 24-measurement trial")
    axis.set_xlabel("Scan")
    axis.set_ylabel("Mean pixel intensity value")
    axis.legend(frameon=False, ncol=2)
    _save(fig, path)


def plot_block_one_distributions(results: AuditResults, path: Path) -> None:
    block_one = results.long.loc[results.long["block"].eq(1)].copy()
    fig, axis = plt.subplots(figsize=(12, 6.2))
    sns.boxplot(
        data=block_one,
        x="scan_id",
        y="value",
        order=SCAN_ORDER,
        color="#8ecae6",
        width=0.62,
        fliersize=2.4,
        linewidth=1,
        ax=axis,
    )
    means = block_one.groupby("scan_id")["value"].mean().reindex(SCAN_ORDER)
    axis.scatter(
        np.arange(len(SCAN_ORDER)),
        means,
        marker="D",
        s=34,
        color="#d1495b",
        label="Mean",
        zorder=4,
    )
    axis.set(title="Trial 1 measurement distributions (the manuscript-analysis trial)")
    axis.set_xlabel("Scan")
    axis.set_ylabel("Pixel intensity value")
    axis.legend(frameon=False)
    axis.text(
        0.995,
        0.98,
        "Boxes summarize nested PIV readings, not independent scan replicates",
        transform=axis.transAxes,
        ha="right",
        va="top",
        color="#495057",
        fontsize=9,
    )
    _save(fig, path)


def plot_matched_differences(results: AuditResults, path: Path) -> None:
    frame = results.matched_pair_sensitivity.copy()
    frame["comparison"] = frame["comparison"].astype(str)
    fig, axis = plt.subplots(figsize=(11, 6))
    sns.barplot(
        data=frame,
        x="comparison",
        y="difference_second_minus_first",
        hue="block",
        order=PAIR_ORDER,
        palette=BLOCK_COLORS,
        edgecolor="white",
        ax=axis,
    )
    axis.axhline(0, color="#343a40", linewidth=1)
    axis.set(title="Sensitivity of matched scan differences across all three trials")
    axis.set_xlabel("Comparison (second scan minus first scan)")
    axis.set_ylabel("Difference in mean pixel intensity")
    axis.legend(title="Trial", frameon=False, ncol=3)
    fig.subplots_adjust(bottom=0.20)
    fig.text(
        0.5,
        0.035,
        "B–C, E–F, G–H, I–J: no alginate → alginate; C–D: tray status",
        ha="center",
        va="center",
        color="#495057",
        fontsize=9,
    )
    _save(fig, path)


def plot_zero_rates(results: AuditResults, path: Path) -> None:
    pivot = results.scan_block_summary.pivot(
        index="scan_id", columns="block", values="zero_percent"
    ).reindex(SCAN_ORDER)
    fig, axis = plt.subplots(figsize=(7.5, 7))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".1f",
        cmap="YlOrRd",
        linewidths=0.6,
        cbar_kws={"label": "Zero-valued cells (%)"},
        ax=axis,
    )
    axis.set(title="Zero-value prevalence by scan and trial")
    axis.set_xlabel("Trial (24 measurements per site)")
    axis.set_ylabel("Scan")
    _save(fig, path)


def plot_control_contrasts(results: AuditResults, path: Path) -> None:
    frame = results.control_tukey_reproduction.copy().iloc[::-1]
    y = np.arange(len(frame))
    fig, axis = plt.subplots(figsize=(9.5, 6.2))
    significant = frame["reject"].astype(bool).to_numpy()
    colors = np.where(significant, "#d1495b", "#457b9d")
    axis.hlines(y, frame["lower"], frame["upper"], color=colors, linewidth=2)
    axis.scatter(frame["meandiff"], y, color=colors, s=50, zorder=3)
    axis.axvline(0, color="#343a40", linewidth=1, linestyle="--")
    axis.set_yticks(y, frame["comparison"])
    axis.set(title="Tukey HSD contrasts against Scan A using trial 1")
    axis.set_xlabel("Mean difference from control with simultaneous 95% CI")
    axis.set_ylabel("Comparison")
    axis.text(
        0.02,
        0.02,
        "Red: adjusted p < 0.05",
        transform=axis.transAxes,
        ha="left",
        va="bottom",
        color="#495057",
        fontsize=9,
    )
    _save(fig, path)


def plot_professor_matched_differences(results: AuditResults, path: Path) -> None:
    frame = results.matched_comparisons.loc[
        results.matched_comparisons["comparison_type"].eq("Alginate vs no alginate")
    ].copy()
    frame = frame.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(frame))
    fig, axis = plt.subplots(figsize=(12, 7.4))
    axis.hlines(
        y,
        frame["first_mean"],
        frame["second_mean"],
        color="#aab7c4",
        linewidth=2.4,
        zorder=1,
    )
    axis.scatter(
        frame["first_mean"],
        y,
        color="#2b6f97",
        s=70,
        label="No alginate",
        zorder=3,
    )
    axis.scatter(
        frame["second_mean"],
        y,
        color="#d97706",
        s=70,
        label="Alginate",
        zorder=3,
    )
    labels = [f"{row.anatomical_site}  ({row.comparison})" for row in frame.itertuples()]
    axis.set_yticks(y, labels)
    axis.set(
        title="Figure 1. Matched peri-implant gray-value means",
        xlabel="Mean gray value across 3 trials (72 measurements per site)",
        ylabel="Matched anatomical site",
    )
    axis.legend(frameon=False, loc="lower right")
    fig.subplots_adjust(bottom=0.16)
    fig.text(
        0.5,
        0.025,
        "Lines connect anatomically matched site rows; values are descriptive, not independent replicates.",
        ha="center",
        va="center",
        color="#495057",
        fontsize=9,
    )
    _save(fig, path)


def plot_professor_intensity_distributions(results: AuditResults, path: Path) -> None:
    frame = results.long.copy()
    fig, axis = plt.subplots(figsize=(12, 6.6))
    sns.boxplot(
        data=frame,
        x="scan_id",
        y="value",
        order=SCAN_ORDER,
        color="#9ecae1",
        width=0.62,
        fliersize=2.2,
        linewidth=1,
        ax=axis,
    )
    trial_means = (
        frame.groupby(["scan_id", "block"], sort=True)["value"].mean().rename("mean").reset_index()
    )
    offsets = {1: -0.16, 2: 0.0, 3: 0.16}
    for trial in (1, 2, 3):
        values = trial_means.loc[trial_means["block"].eq(trial)].set_index("scan_id")
        axis.scatter(
            np.arange(len(SCAN_ORDER)) + offsets[trial],
            values.loc[SCAN_ORDER, "mean"],
            color=BLOCK_COLORS[trial],
            s=30,
            marker="D",
            label=f"Trial {trial} mean",
            zorder=4,
        )
    axis.set(
        title="Figure 2. Gray-value distributions across all three trials",
        xlabel="Scan",
        ylabel="Peri-implant gray value",
    )
    axis.legend(frameon=False, ncol=3, loc="upper left")
    fig.subplots_adjust(bottom=0.16)
    fig.text(
        0.5,
        0.025,
        "Boxes pool nested measurements; circles are displayed as outliers by the 1.5×IQR rule.",
        ha="center",
        va="center",
        color="#495057",
        fontsize=9,
    )
    _save(fig, path)


def create_figures(results: AuditResults, output_dir: str | Path) -> dict[str, str]:
    """Create aggregate-only figures and return report-relative paths."""

    _style()
    figure_dir = Path(output_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)
    figures = {
        "block_means": "scan_block_means.png",
        "block_one_distributions": "block_1_distributions.png",
        "matched_differences": "matched_pair_sensitivity.png",
        "zero_rates": "zero_rate_heatmap.png",
        "control_contrasts": "control_tukey_contrasts.png",
        "figure_1_matched": "figure_1_matched_differences.png",
        "figure_2_distributions": "figure_2_intensity_distributions.png",
    }
    plot_block_means(results, figure_dir / figures["block_means"])
    plot_block_one_distributions(results, figure_dir / figures["block_one_distributions"])
    plot_matched_differences(results, figure_dir / figures["matched_differences"])
    plot_zero_rates(results, figure_dir / figures["zero_rates"])
    plot_control_contrasts(results, figure_dir / figures["control_contrasts"])
    plot_professor_matched_differences(results, figure_dir / figures["figure_1_matched"])
    plot_professor_intensity_distributions(results, figure_dir / figures["figure_2_distributions"])
    return {name: f"figures/{filename}" for name, filename in figures.items()}
