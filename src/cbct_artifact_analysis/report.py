"""Generate a self-contained narrative audit around aggregate tables and figures."""

from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

import pandas as pd
from jinja2 import BaseLoader, Environment

from cbct_artifact_analysis.analysis import AuditResults, rounded_for_export


def _format_cell(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _markdown_table(frame: pd.DataFrame) -> str:
    display = rounded_for_export(frame)
    headers = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in display.itertuples(index=False, name=None):
        cells = [_format_cell(value).replace("|", "\\|") for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _html_table(frame: pd.DataFrame) -> str:
    display = rounded_for_export(frame)
    headers = "".join(f"<th>{escape(str(column))}</th>" for column in display.columns)
    rows = []
    for row in display.itertuples(index=False, name=None):
        cells = "".join(f"<td>{escape(_format_cell(value))}</td>" for value in row)
        rows.append(f"<tr>{cells}</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def _report_context(results: AuditResults, figures: dict[str, str]) -> dict[str, object]:
    values = results.long["value"]
    block_means = results.scan_block_summary.pivot(index="scan_id", columns="block", values="mean")
    matched = results.matched_pair_sensitivity
    alginate_pairs = matched.loc[matched["comparison"].isin(["B-C", "E-F", "G-H", "I-J"])]
    all_positive = bool(alginate_pairs["difference_second_minus_first"].gt(0).all())
    professor_matched = results.matched_comparisons.loc[
        results.matched_comparisons["comparison_type"].eq("Alginate vs no alginate")
    ]
    positive_site_count = int(professor_matched["difference_second_minus_first"].gt(0).sum())
    means_display = results.manuscript_reproduction.rename(
        columns={"workbook_block_1_mean": "workbook_trial_1_mean"}
    )
    sensitivity_display = results.matched_pair_sensitivity.rename(columns={"block": "trial"})
    paired_display = results.paired_trial_analysis[
        [
            "comparison",
            "comparison_type",
            "n_trial_pairs",
            "first_mean_across_trials",
            "second_mean_across_trials",
            "mean_paired_difference",
            "paired_difference_sd",
            "difference_ci95_lower",
            "difference_ci95_upper",
            "exact_sign_flip_p",
        ]
    ]
    return {
        "generated_date": date.today().isoformat(),
        "profile": results.profile,
        "measurement_count": len(values),
        "zero_count": int(values.eq(0).sum()),
        "zero_percent": 100 * float(values.eq(0).mean()),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "mean_reproduction_count": int(results.manuscript_reproduction["reproduces_at_2dp"].sum()),
        "control_p_reproduction_count": int(
            results.control_tukey_reproduction["reproduces_at_3dp"].sum()
        ),
        "all_positive": "Yes" if all_positive else "No",
        "positive_site_count": positive_site_count,
        "matched_site_count": len(professor_matched),
        "matched_difference_min": float(professor_matched["difference_second_minus_first"].min()),
        "matched_difference_max": float(professor_matched["difference_second_minus_first"].max()),
        "block_range_low": float(block_means.min(axis=1).min()),
        "block_range_high": float(block_means.max(axis=1).max()),
        "figures": figures,
        "quality_md": _markdown_table(results.quality_summary),
        "table_1_md": _markdown_table(results.experimental_design),
        "table_2_md": _markdown_table(results.site_descriptive_statistics),
        "table_3_md": _markdown_table(results.matched_comparisons),
        "means_md": _markdown_table(means_display),
        "tukey_md": _markdown_table(results.control_tukey_reproduction),
        "matched_md": _markdown_table(sensitivity_display),
        "paired_md": _markdown_table(paired_display),
        "matched_p_md": _markdown_table(results.matched_p_reproduction),
        "quality_html": _html_table(results.quality_summary),
        "table_1_html": _html_table(results.experimental_design),
        "table_2_html": _html_table(results.site_descriptive_statistics),
        "table_3_html": _html_table(results.matched_comparisons),
        "means_html": _html_table(means_display),
        "tukey_html": _html_table(results.control_tukey_reproduction),
        "matched_html": _html_table(sensitivity_display),
        "paired_html": _html_table(paired_display),
        "matched_p_html": _html_table(results.matched_p_reproduction),
    }


MARKDOWN_TEMPLATE = """# CBCT alginate study: data audit and visualization report

Generated: {{ generated_date }}

## Executive finding

The workbook is structurally complete at the cell level, but it is not analysis-ready without a
data dictionary. It contains **{{ measurement_count }} numeric measurements** across 18 implant-site
rows and 10 scans, arranged as three trial blocks of 24 values. The manuscripts describe 24 PIV
measurements per site (eight points at three radii); the spreadsheet contains three such trials.

The published scan means reproduce for **{{ mean_reproduction_count }}/10 scans** only when the
first 24-measurement trial is used. The reported Scan A comparison p-values reproduce for
**{{ control_p_reproduction_count }}/9 contrasts** as a ten-group Tukey HSD on those same trial 1
measurements. This makes the computation traceable, but it does not resolve whether trial 1 was a
pre-specified endpoint or why trials 2 and 3 were excluded from the reported values.

Across all three trials, all four like-for-like alginate contrasts (B–C, E–F, G–H, I–J) have a
positive descriptive change in mean PIV: **{{ all_positive }}**. This directional consistency is
useful, but it is not by itself evidence of statistical independence or generalizability.

> Privacy: the source workbook remains under `data/private/`, is ignored by Git, and is never
> exported in row-level form. This report and its CSV tables contain aggregates only.

## Workbook audit

{{ quality_md }}

Important structural observations:

- There is no header row, codebook, formula, validation rule, Excel table, or cell comment defining
  the 72 numeric columns.
- Six merged scan-label ranges require carrying the scan label down to secondary implant sites.
- {{ zero_count }} cells ({{ "%.1f"|format(zero_percent) }}%) are exactly zero. Zero may be a valid
  PIV, clipping/background, or missingness encoded as zero; the workbook does not say which.
- Rows after the 18 data rows contain free-text requested comparisons, not observations.
- The workbook does not contain the qualitative Likert ratings described in the manuscripts, so
  inter-rater reliability and qualitative conclusions cannot be audited here.

![Zero-value prevalence]({{ figures.zero_rates }})

The complete scan/site/trial zero audit is exported as
`tables/zero_audit_by_scan_site_trial.csv`. Zeros are counted and retained; none are deleted or
converted to missing values.

## Corrected study framing

**Revised objective.** To characterize and compare peri-implant CBCT gray-value distributions at
standardized sampling locations around titanium implants in matched scan configurations acquired
with and without alginate, and to assess consistency across three trials and tray status.

**Revised hypothesis.** The null hypothesis is that matched alginate and no-alginate scans have the
same peri-implant gray-value distribution. The research hypothesis is that the distributions differ.
The direction and magnitude are estimated rather than presupposed. Gray-value differences are a
surrogate imaging outcome and do not, by themselves, demonstrate that metal artifact was reduced or
worsened.

The study remains a CBCT metal-artifact study. Optical scanning, dimensional accuracy, and material
shrinkage are outside the dataset and are not interpreted.

## Table 1. Experimental design

{{ table_1_md }}

## Table 2. Site-level descriptive statistics

Each row summarizes all 72 retained measurements for one site (3 trials × 24 measurements).

{{ table_2_md }}

## Manuscript mean reproduction

{{ means_md }}

Nine printed means match trial 1 after rounding to two decimals. Scan F is 632.2047 in the workbook
(632.20 at two decimals) but 632.21 in both manuscripts. Every absolute discrepancy is below 0.006,
so trial 1 is clearly the source, but the Scan F rounding/source-version discrepancy should be fixed.
Using all three trials changes the descriptive scan means, demonstrating that the trial selection
choice is analytically material.

![Scan means across trials]({{ figures.block_means }})

![Trial 1 distributions]({{ figures.block_one_distributions }})

## Reported Scan A comparisons

{{ tukey_md }}

These values reproduce a Tukey HSD across ten scan-ID groups using trial 1. The individual PIV
locations are nested within implant sites and scan acquisitions. Treating them as independent
replicates is therefore a likely pseudoreplication risk unless the protocol supplies a defensible
independence argument. The control also has no implant, so its contrast with implant scans combines
implant presence, implant number/location, and alginate/tray conditions.

![Control contrasts]({{ figures.control_contrasts }})

## Table 3. Matched comparisons

The four alginate/no-alginate scan pairs are matched at their component anatomical sites. C–D is
listed separately because both scans are labelled as containing alginate and differ in tray status.
No point-level p-values are presented in this table.

{{ table_3_md }}

## Figure 1. Matched differences

![Matched peri-implant means]({{ figures.figure_1_matched }})

## Figure 2. Intensity distributions

![All-trial intensity distributions]({{ figures.figure_2_distributions }})

## Trial sensitivity analysis

{{ matched_md }}

![Matched contrasts across trials]({{ figures.matched_differences }})

## Paired trial-level analysis

{{ paired_md }}

The paired unit here is the 24-measurement trial mean, not an individual PIV location. The exact
two-sided sign-flip p-value is 0.25 for every comparison: with only three trial pairs, 0.25 is the
smallest attainable two-sided value when all three differences have the same sign. The t-based 95%
intervals are shown descriptively, but normality cannot be assessed with three pairs. More
importantly, the trials may be technical repeats rather than independent scan acquisitions. These
results therefore do not establish statistical significance; independent acquisition-level
replication is needed for confirmatory inference.

## Secondary RTM feasibility analysis

The grouped feasibility experiment is reported separately in `rtm_feasibility_report.md`. The
confirmed-design Regression Tsetlin Machine had pooled MAE/RMSE of 413.9/501.2 gray-value units,
compared with 400.7/485.8 for linear regression and 409.0/490.3 for the rule baseline. Its clauses
mainly restated condition, tray, anatomy, and trial patterns already visible descriptively. The RTM
should **not** be retained as a manuscript result; it may remain as a reproducible appendix or
future-work note. The model that adds positions 1–24 is sensitivity-only because those column
positions are not validated radius/direction labels.

The manuscript's second p-value table is not reproduced by applying the same ten-group Tukey HSD
to trial 1:

{{ matched_p_md }}

The analysis method for the manuscript's E–F, G–H, and I–J p-values must be documented before those
values are relied upon. In particular, the G–H value differs substantially from the ten-group Tukey
result, and the I–J conclusion is close to 0.05 in the manuscript.

## Statistical and study-design risks

1. **Incomplete measurement schema.** The 72 cells per site need explicit trial, radius, direction,
   slice/repeat, observer, units, and zero-value definitions.
2. **Unexplained endpoint selection.** Two-thirds of the stored measurements are absent from the
   manuscript mean calculation. Selection should be justified prospectively or all trials analyzed
   with a stated repeated-measures model.
3. **Experimental unit ambiguity.** Multiple PIV points from the same scan are correlated technical
   measurements, not obviously independent biological/scan replicates. Confidence intervals and
   p-values based on point-level independence may be too optimistic.
4. **Condition confounding.** Scan identity changes implant number and location as well as alginate.
   Scan A additionally changes implant presence. Primary alginate inference should use matched
   configurations and appropriate scan/site-level replication.
5. **Incomplete audit trail.** Raw CBCT identifiers, ROI coordinates, slice identifiers, extraction
   code/version, and qualitative scores are not linked from the workbook.
6. **Reporting issues.** Report values below 0.001 as `p < 0.001`, never `p = 0.000`; report effect
   sizes and confidence intervals alongside multiplicity-adjusted p-values.

## Recommended remediation before submission

1. Freeze a data dictionary mapping every column and site code, including what trials 1–3 and zero
   mean; preserve the workbook unchanged as a read-only source artifact outside Git.
2. Reconcile the primary endpoint with all three trials and document why the existing manuscript
   used trial 1 only.
3. Identify the experimental unit and fit a pre-specified repeated/mixed-effects analysis (for
   example, measurements nested within implant/site and scan/skull) only if the number of
   independent units supports it. Otherwise present this as an exploratory/descriptive ex-vivo
   study and collect independent replicates for confirmatory inference.
4. Document and reproduce the matched-pair p-value method. Prefer planned B–C, E–F, G–H, and I–J
   contrasts with effect estimates and confidence intervals.
5. Add qualitative ratings with blinded reader IDs and calculate agreement (weighted kappa or an
   ordinal mixed model, as justified by the protocol).
6. Version the analysis environment and record software versions, input checksum, and a signed-off
   analysis run for the final manuscript.
7. Keep the current RTM feasibility experiment outside the manuscript results unless independent
   validation data and a signed-off measurement-position map support a new analysis.

## Reproduction

```powershell
python -m pip install -e ".[dev]"
python -m cbct_artifact_analysis run
.\\scripts\\run_rtm_feasibility.ps1
python -m pytest
python scripts/privacy_guard.py --tracked
```
"""


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CBCT alginate study — data audit</title>
<style>
:root { --ink:#172033; --muted:#526071; --navy:#12355b; --blue:#2b6f97; --paper:#fff; --bg:#f3f6f9; --line:#dbe3ea; --warn:#fff4db; --danger:#9d2a3a; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.62 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { width:min(1120px, calc(100% - 32px)); margin:32px auto 64px; background:var(--paper); padding:clamp(28px,5vw,68px); box-shadow:0 18px 50px rgba(18,53,91,.09); border-radius:16px; }
h1,h2,h3 { color:var(--navy); line-height:1.2; }
h1 { font-size:clamp(2rem,4vw,3.1rem); margin:.1em 0 .2em; }
h2 { margin-top:2.2em; padding-top:.3em; border-top:2px solid var(--line); }
.eyebrow { color:var(--blue); font-weight:700; letter-spacing:.1em; text-transform:uppercase; font-size:.78rem; }
.lede { font-size:1.13rem; color:#334155; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin:26px 0; }
.card { background:#f7fafc; border:1px solid var(--line); border-radius:12px; padding:18px; }
.card strong { display:block; font-size:1.65rem; color:var(--navy); }
.callout { border-left:5px solid var(--blue); background:#edf6fb; padding:15px 18px; border-radius:8px; }
.warning { border-left-color:#d98e04; background:var(--warn); }
figure { margin:32px 0; }
figure img { display:block; width:100%; height:auto; border:1px solid var(--line); border-radius:10px; }
figcaption { color:var(--muted); font-size:.9rem; margin-top:8px; }
.table-wrap { width:100%; overflow-x:auto; margin:18px 0 28px; border:1px solid var(--line); border-radius:10px; }
table { border-collapse:collapse; width:100%; font-size:.89rem; }
th { background:var(--navy); color:white; text-align:left; position:sticky; top:0; }
th,td { padding:9px 11px; border-bottom:1px solid var(--line); white-space:nowrap; }
tbody tr:nth-child(even) { background:#f8fafc; }
code { background:#edf1f5; border-radius:4px; padding:.08em .32em; }
pre { background:#101827; color:#e6edf3; padding:17px; border-radius:9px; overflow:auto; }
ol li, ul li { margin:.5em 0; }
.footer { margin-top:48px; color:var(--muted); font-size:.9rem; }
@media print { body{background:white} main{box-shadow:none;margin:0;width:100%;padding:24px} .table-wrap{overflow:visible} }
</style>
</head>
<body><main>
<div class="eyebrow">Reproducible research audit · {{ generated_date }}</div>
<h1>CBCT alginate study<br>data audit &amp; visualization</h1>
<p class="lede">The workbook is cell-complete, but the measurement schema and experimental unit
must be resolved before its inferential results are submission-ready.</p>

<div class="cards">
  <div class="card"><strong>{{ measurement_count }}</strong>numeric measurements</div>
  <div class="card"><strong>18</strong>implant-site rows</div>
  <div class="card"><strong>{{ mean_reproduction_count }}/10</strong>means reproduced</div>
  <div class="card"><strong>{{ "%.1f"|format(zero_percent) }}%</strong>exactly zero</div>
</div>

<div class="callout"><strong>Privacy boundary.</strong> The workbook remains in <code>data/private/</code>,
is ignored by Git, and is never exported row-by-row. All tables and figures below are aggregate.</div>

<h2>Executive finding</h2>
<p>The workbook holds 72 values per site in three 24-measurement trial blocks. The manuscripts
describe 24 values per site. Nine of ten scan means reproduce at two decimals from trial 1; Scan F
is 632.2047 in the workbook (632.20 at two decimals) but 632.21 in both manuscripts. All nine Scan A
p-values reproduce as a ten-group Tukey HSD on trial 1. That identifies the prior calculation but
leaves two-thirds of the stored measurements unexplained.</p>
<p>All four like-for-like alginate comparisons move toward higher mean PIV in all three trials.
This is descriptively consistent, but the PIV locations are nested technical readings within scans;
they are not automatically independent experimental replicates.</p>

<h2>Workbook audit</h2>
{{ quality_html | safe }}
<ul>
<li>No header row, codebook, formulas, validations, structured table, or cell comments define the 72 columns.</li>
<li>Six merged scan labels must be carried down to secondary implant sites.</li>
<li>{{ zero_count }} values are zero; the file does not define whether zero is valid PIV, clipping/background, or encoded missingness.</li>
<li>Qualitative Likert ratings are absent, so inter-rater reliability cannot be audited.</li>
</ul>
<figure><img src="{{ figures.zero_rates }}" alt="Heatmap of zero rates"><figcaption>Zero prevalence varies by scan and trial. Zeros were retained.</figcaption></figure>
<p>The complete scan/site/trial zero audit is available in
<code>tables/zero_audit_by_scan_site_trial.csv</code>.</p>

<h2>Corrected study framing</h2>
<p><strong>Revised objective.</strong> To characterize and compare peri-implant CBCT gray-value
distributions at standardized sampling locations around titanium implants in matched scan
configurations acquired with and without alginate, and to assess consistency across three trials
and tray status.</p>
<p><strong>Revised hypothesis.</strong> The null hypothesis is that matched alginate and no-alginate
scans have the same peri-implant gray-value distribution. The research hypothesis is that the
distributions differ. Direction and magnitude are estimated rather than presupposed. Gray-value
differences are a surrogate imaging outcome and do not by themselves demonstrate artifact reduction
or worsening.</p>
<p>The study remains a CBCT metal-artifact study. Optical scanning, dimensional accuracy, and
material shrinkage are outside the dataset and are not interpreted.</p>

<h2>Table 1. Experimental design</h2>
{{ table_1_html | safe }}

<h2>Table 2. Site-level descriptive statistics</h2>
<p>Each row summarizes all 72 retained measurements for one site (3 trials × 24 measurements).</p>
{{ table_2_html | safe }}

<h2>Manuscript mean reproduction</h2>
{{ means_html | safe }}
<figure><img src="{{ figures.block_means }}" alt="Scan means across all trials"><figcaption>The printed manuscript means derive from trial 1; Scan F differs by 0.0053.</figcaption></figure>
<figure><img src="{{ figures.block_one_distributions }}" alt="Trial 1 distributions"><figcaption>Point distributions are descriptive; points are nested within scan/site.</figcaption></figure>

<h2>Scan A comparisons</h2>
{{ tukey_html | safe }}
<div class="callout warning"><strong>Inference warning.</strong> Tukey's multiplicity adjustment is
reproduced, but the calculation treats nested PIV locations as group observations. Unless their
independence is defensible, standard errors may be too small. Scan A also differs by implant presence.</div>
<figure><img src="{{ figures.control_contrasts }}" alt="Tukey contrasts against control"><figcaption>Simultaneous 95% intervals from the reproduced trial 1 Tukey model.</figcaption></figure>

<h2>Table 3. Matched comparisons</h2>
<p>The alginate/no-alginate scans are paired by anatomical site. C–D is separate because both scans
are labelled as containing alginate and differ in tray status. No point-level p-values are reported.</p>
{{ table_3_html | safe }}

<h2>Figure 1. Matched differences</h2>
<figure><img src="{{ figures.figure_1_matched }}" alt="Matched peri-implant gray-value means"><figcaption>Lines connect the no-alginate and alginate mean for each comparable anatomical site.</figcaption></figure>

<h2>Figure 2. Intensity distributions</h2>
<figure><img src="{{ figures.figure_2_distributions }}" alt="All-trial gray-value distributions"><figcaption>Boxplots show variability and outliers; trial means are overlaid.</figcaption></figure>

<h2>Trial sensitivity analysis</h2>
{{ matched_html | safe }}
<figure><img src="{{ figures.matched_differences }}" alt="Matched differences across trials"><figcaption>Positive B–C, E–F, G–H and I–J values mean the alginate scan had higher mean PIV.</figcaption></figure>
<h2>Paired trial-level analysis</h2>
{{ paired_html | safe }}
<div class="callout warning"><strong>Exploratory inference only.</strong> The exact two-sided
sign-flip p-value is 0.25 for every comparison, the minimum possible with three same-direction
pairs. Trials may be technical repeats rather than independent acquisitions, so these results do
not establish statistical significance.</div>
<h2>Secondary RTM feasibility analysis</h2>
<p>The confirmed-design Regression Tsetlin Machine had pooled MAE/RMSE of 413.9/501.2 gray-value
units, compared with 400.7/485.8 for linear regression and 409.0/490.3 for the rule baseline. Its
clauses mainly restated already-visible condition, tray, anatomy, and trial patterns. It should not
be retained as a manuscript result. See <code>rtm_feasibility_report.md</code>; the 1–24 position
variant is sensitivity-only because those positions lack validated radius/direction labels.</p>
<h3>Unresolved manuscript p-values</h3>
<p>The manuscript does not name the method for its second p-value table. Applying the same ten-group
Tukey analysis does not reproduce those three values:</p>
{{ matched_p_html | safe }}

<h2>Risks requiring resolution</h2>
<ol>
<li><strong>Incomplete schema:</strong> define trial, radius, direction, repeat/slice, observer, unit, and zero semantics.</li>
<li><strong>Endpoint selection:</strong> explain why trial 1 was primary or reanalyze all trials using a stated repeated-measures model.</li>
<li><strong>Experimental unit:</strong> PIV points within a scan are correlated; identify independent skull/scan/implant replication.</li>
<li><strong>Confounding:</strong> scan IDs change implant number/location and alginate; Scan A also removes the implant.</li>
<li><strong>Audit trail:</strong> link CBCT IDs, ROI/slice coordinates, extraction code/version, and qualitative scores.</li>
<li><strong>Reporting:</strong> use <code>p &lt; 0.001</code>, not <code>p = 0.000</code>, and report effects with intervals.</li>
</ol>

<h2>Recommended remediation</h2>
<ol>
<li>Freeze a signed-off data dictionary and preserve the workbook as an immutable private source.</li>
<li>Reconcile all three trials with the manuscript endpoint before further inference.</li>
<li>Use planned matched contrasts and a justified hierarchical/repeated model only when independent replication supports it.</li>
<li>Document and reproduce the E–F, G–H, and I–J p-value method.</li>
<li>Add blinded qualitative ratings and a justified inter-rater agreement analysis.</li>
<li>Archive the final environment, source checksum, software versions, and analysis log.</li>
<li>Keep the current RTM outside the manuscript results unless independent validation and a signed-off position map support re-analysis.</li>
</ol>

<h2>Reproduce locally</h2>
<pre><code>python -m pip install -e ".[dev]"
python -m cbct_artifact_analysis run
.\\scripts\\run_rtm_feasibility.ps1
python -m pytest
python scripts/privacy_guard.py --tracked</code></pre>

<p class="footer">Generated from the private master workbook by the versioned analysis pipeline.
No row-level measurements are embedded in this report.</p>
</main></body></html>
"""


MEETING_TEMPLATE = """# One-page meeting summary: CBCT alginate study

Prepared: {{ generated_date }}

## Study question

Do peri-implant CBCT gray-value distributions differ between anatomically matched scans acquired
with and without alginate, and are the descriptive differences consistent across three trials?
Scan C versus D is a separate tray-status sensitivity comparison.

## Proposed objective and hypothesis

**Objective:** Characterize and compare peri-implant CBCT gray-value distributions at standardized
sampling locations around titanium implants in matched scan configurations acquired with and without
alginate, and assess consistency across three trials and tray status.

**Hypothesis:** The null is that matched alginate and no-alginate scans have the same gray-value
distribution; the research hypothesis is that the distributions differ. Direction and magnitude
will be estimated. Gray values are a surrogate imaging outcome and do not alone prove that metal
artifact was reduced or worsened. Optical scanning, dimensional accuracy, and material shrinkage
are outside the study.

## Preliminary results

- The spreadsheet contains 18 site rows and {{ measurement_count }} numeric values: 72 per site,
  organized as 3 trials × 24 measurements. There are no blank or non-numeric measurement cells.
- {{ zero_count }} values ({{ "%.1f"|format(zero_percent) }}%) are exactly zero. They were retained.
  Their physical/data-processing meaning still needs confirmation.
- Nine of ten manuscript scan means reproduce from trial 1 at two decimals. Scan F is 632.2047 in
  the spreadsheet (632.20) versus 632.21 in the manuscripts.
- All nine Scan A adjusted p-values reproduce as a ten-group Tukey HSD on trial 1, identifying the
  prior calculation but not validating its independence assumption.
- {{ positive_site_count }}/{{ matched_site_count }} anatomically matched site rows have a higher
  overall mean in the alginate scan. Descriptive differences range from
  {{ "%.1f"|format(matched_difference_min) }} to {{ "%.1f"|format(matched_difference_max) }} gray-value
  units. These are exploratory summaries, not independent replicated effects.
- The reported E–F, G–H, and I–J p-values are not reproduced by the same Tukey procedure; the
  original method needs to be identified.
- Trial-mean paired differences are directionally positive in all five planned comparisons, but
  every exact two-sided sign-flip p-value is 0.25. With only three possibly technical trial pairs,
  this does not establish statistical significance.
- In five-fold leave-one-configuration-out validation, the confirmed-design RTM had pooled
  MAE/RMSE 413.9/501.2, versus 400.7/485.8 for linear regression and 409.0/490.3 for the rule
  baseline. Its clauses mostly repeated known condition/tray/anatomy patterns. Do not retain it as
  a manuscript result; keep it as an appendix or future-work note.

## Main limitations

1. The 24 within-trial columns lack radius/direction labels; the meaning of exact zero is unknown.
2. Multiple points from one scan are repeated technical measurements. Treating them as independent
   samples is likely pseudoreplication and can make confidence intervals and p-values too optimistic.
3. Scan A has no implant, so comparisons with A combine implant presence with other conditions.
4. Scan configurations vary by implant number and anatomy; alginate inference should emphasize
   B–C, E–F, G–H, and I–J, with C–D reported separately.
5. The workbook does not contain independent skull/acquisition identifiers, ROI coordinates,
   qualitative reader scores, or extraction provenance.

## Decisions needed at the meeting

1. Confirm that the three 24-column groups are trials and provide the within-trial radius/direction
   order.
2. Define zero values: observed gray value, clipping/background, or encoded missingness.
3. Confirm Scan D's exact condition after tray removal and the intended C–D interpretation.
4. Identify the statistical procedure/software used for the second manuscript p-value table.
5. Confirm the number of independent skulls and scan acquisitions. If there is one acquisition per
   condition, present inference as exploratory and plan independent replication.
6. Keep the current RTM feasibility result outside the manuscript results. Reconsider it only with
   independent validation data and a signed-off mapping for positions 1–24.
7. Approve the revised objective/hypothesis and supply qualitative ratings if those conclusions will
   remain in the manuscript.

## Requested meeting outcome

Approve the data dictionary, experimental unit, primary matched contrasts, role of all three trials,
whether the current work is a descriptive pilot or has enough independent replication for a
confirmatory mixed/repeated-measures analysis, and the decision to exclude the current RTM result
from the manuscript.
"""


def write_reports(
    results: AuditResults, figures: dict[str, str], output_dir: str | Path
) -> tuple[Path, Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    context = _report_context(results, figures)
    environment = Environment(loader=BaseLoader(), autoescape=False, keep_trailing_newline=True)
    markdown = environment.from_string(MARKDOWN_TEMPLATE).render(**context)
    html = environment.from_string(HTML_TEMPLATE).render(**context)
    meeting_summary = environment.from_string(MEETING_TEMPLATE).render(**context)
    markdown_path = output / "data_audit_report.md"
    html_path = output / "data_audit_report.html"
    meeting_path = output / "meeting_summary.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    meeting_path.write_text(meeting_summary, encoding="utf-8")
    return markdown_path, html_path, meeting_path
