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
        "block_range_low": float(block_means.min(axis=1).min()),
        "block_range_high": float(block_means.max(axis=1).max()),
        "figures": figures,
        "quality_md": _markdown_table(results.quality_summary),
        "means_md": _markdown_table(results.manuscript_reproduction),
        "tukey_md": _markdown_table(results.control_tukey_reproduction),
        "matched_md": _markdown_table(results.matched_pair_sensitivity),
        "matched_p_md": _markdown_table(results.matched_p_reproduction),
        "quality_html": _html_table(results.quality_summary),
        "means_html": _html_table(results.manuscript_reproduction),
        "tukey_html": _html_table(results.control_tukey_reproduction),
        "matched_html": _html_table(results.matched_pair_sensitivity),
        "matched_p_html": _html_table(results.matched_p_reproduction),
    }


MARKDOWN_TEMPLATE = """# CBCT alginate study: data audit and visualization report

Generated: {{ generated_date }}

## Executive finding

The workbook is structurally complete at the cell level, but it is not analysis-ready without a
data dictionary. It contains **{{ measurement_count }} numeric measurements** across 18 implant-site
rows and 10 scans, arranged as three unlabelled blocks of 24 values. The manuscripts describe only
24 PIV measurements per site (eight points at three radii), while the workbook stores 72.

The published scan means reproduce for **{{ mean_reproduction_count }}/10 scans** only when the
first 24-value block is used. The reported Scan A comparison p-values reproduce for
**{{ control_p_reproduction_count }}/9 contrasts** as a ten-group Tukey HSD on those same block 1
measurements. This makes the computation traceable, but it does not resolve whether block 1 was a
pre-specified endpoint or why blocks 2 and 3 were excluded.

Across all three blocks, all four like-for-like alginate contrasts (B–C, E–F, G–H, I–J) have a
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

## Manuscript mean reproduction

{{ means_md }}

Nine printed means match block 1 after rounding to two decimals. Scan F is 632.2047 in the workbook
(632.20 at two decimals) but 632.21 in both manuscripts. Every absolute discrepancy is below 0.006,
so block 1 is clearly the source, but the Scan F rounding/source-version discrepancy should be fixed.
Using all three blocks changes the descriptive scan means, demonstrating that the unlabelled block
choice is analytically material.

![Scan means across blocks]({{ figures.block_means }})

![Block 1 distributions]({{ figures.block_one_distributions }})

## Reported Scan A comparisons

{{ tukey_md }}

These values reproduce a Tukey HSD across ten scan-ID groups using block 1. The individual PIV
locations are nested within implant sites and scan acquisitions. Treating them as independent
replicates is therefore a likely pseudoreplication risk unless the protocol supplies a defensible
independence argument. The control also has no implant, so its contrast with implant scans combines
implant presence, implant number/location, and alginate/tray conditions.

![Control contrasts]({{ figures.control_contrasts }})

## Matched-configurations sensitivity analysis

{{ matched_md }}

![Matched contrasts across blocks]({{ figures.matched_differences }})

The manuscript's second p-value table is not reproduced by applying the same ten-group Tukey HSD
to block 1:

{{ matched_p_md }}

The analysis method for the manuscript's E–F, G–H, and I–J p-values must be documented before those
values are relied upon. In particular, the G–H value differs substantially from the ten-group Tukey
result, and the I–J conclusion is close to 0.05 in the manuscript.

## Statistical and study-design risks

1. **Unknown measurement schema.** The 72 cells per site need explicit block, radius, direction,
   slice/repeat, observer, units, and zero-value definitions.
2. **Unexplained endpoint selection.** Two-thirds of the stored measurements are absent from the
   manuscript mean calculation. Selection should be justified prospectively or all blocks analyzed
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

1. Freeze a data dictionary mapping every column and site code, including what blocks 1–3 and zero
   mean; preserve the workbook unchanged as a read-only source artifact outside Git.
2. Reconcile the primary endpoint with all three blocks and document why the existing manuscript
   used block 1 only.
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

## Reproduction

```powershell
python -m pip install -e ".[dev]"
python -m cbct_artifact_analysis run
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
<p>The workbook holds 72 values per site in three unlabelled 24-value blocks. The manuscripts
describe 24 values per site. Nine of ten scan means reproduce at two decimals from block 1; Scan F
is 632.2047 in the workbook (632.20 at two decimals) but 632.21 in both manuscripts. All nine Scan A
p-values reproduce as a ten-group Tukey HSD on block 1. That identifies the prior calculation but
leaves two-thirds of the stored measurements unexplained.</p>
<p>All four like-for-like alginate comparisons move toward higher mean PIV in all three blocks.
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
<figure><img src="{{ figures.zero_rates }}" alt="Heatmap of zero rates"><figcaption>Zero prevalence varies by scan and unlabelled block.</figcaption></figure>

<h2>Manuscript mean reproduction</h2>
{{ means_html | safe }}
<figure><img src="{{ figures.block_means }}" alt="Scan means across all blocks"><figcaption>The printed manuscript means derive from block 1; Scan F differs by 0.0053.</figcaption></figure>
<figure><img src="{{ figures.block_one_distributions }}" alt="Block 1 distributions"><figcaption>Point distributions are descriptive; points are nested within scan/site.</figcaption></figure>

<h2>Scan A comparisons</h2>
{{ tukey_html | safe }}
<div class="callout warning"><strong>Inference warning.</strong> Tukey's multiplicity adjustment is
reproduced, but the calculation treats nested PIV locations as group observations. Unless their
independence is defensible, standard errors may be too small. Scan A also differs by implant presence.</div>
<figure><img src="{{ figures.control_contrasts }}" alt="Tukey contrasts against control"><figcaption>Simultaneous 95% intervals from the reproduced block 1 Tukey model.</figcaption></figure>

<h2>Matched-configuration sensitivity</h2>
{{ matched_html | safe }}
<figure><img src="{{ figures.matched_differences }}" alt="Matched differences across blocks"><figcaption>Positive B–C, E–F, G–H and I–J values mean the alginate scan had higher mean PIV.</figcaption></figure>
<h3>Unresolved manuscript p-values</h3>
<p>The manuscript does not name the method for its second p-value table. Applying the same ten-group
Tukey analysis does not reproduce those three values:</p>
{{ matched_p_html | safe }}

<h2>Risks requiring resolution</h2>
<ol>
<li><strong>Unknown schema:</strong> define block, radius, direction, repeat/slice, observer, unit, and zero semantics.</li>
<li><strong>Endpoint selection:</strong> explain why block 1 was primary or reanalyze all blocks using a stated repeated-measures model.</li>
<li><strong>Experimental unit:</strong> PIV points within a scan are correlated; identify independent skull/scan/implant replication.</li>
<li><strong>Confounding:</strong> scan IDs change implant number/location and alginate; Scan A also removes the implant.</li>
<li><strong>Audit trail:</strong> link CBCT IDs, ROI/slice coordinates, extraction code/version, and qualitative scores.</li>
<li><strong>Reporting:</strong> use <code>p &lt; 0.001</code>, not <code>p = 0.000</code>, and report effects with intervals.</li>
</ol>

<h2>Recommended remediation</h2>
<ol>
<li>Freeze a signed-off data dictionary and preserve the workbook as an immutable private source.</li>
<li>Reconcile all three blocks with the manuscript endpoint before further inference.</li>
<li>Use planned matched contrasts and a justified hierarchical/repeated model only when independent replication supports it.</li>
<li>Document and reproduce the E–F, G–H, and I–J p-value method.</li>
<li>Add blinded qualitative ratings and a justified inter-rater agreement analysis.</li>
<li>Archive the final environment, source checksum, software versions, and analysis log.</li>
</ol>

<h2>Reproduce locally</h2>
<pre><code>python -m pip install -e ".[dev]"
python -m cbct_artifact_analysis run
python -m pytest
python scripts/privacy_guard.py --tracked</code></pre>

<p class="footer">Generated from the private master workbook by the versioned analysis pipeline.
No row-level measurements are embedded in this report.</p>
</main></body></html>
"""


def write_reports(
    results: AuditResults, figures: dict[str, str], output_dir: str | Path
) -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    context = _report_context(results, figures)
    environment = Environment(loader=BaseLoader(), autoescape=False, keep_trailing_newline=True)
    markdown = environment.from_string(MARKDOWN_TEMPLATE).render(**context)
    html = environment.from_string(HTML_TEMPLATE).render(**context)
    markdown_path = output / "data_audit_report.md"
    html_path = output / "data_audit_report.html"
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return markdown_path, html_path
