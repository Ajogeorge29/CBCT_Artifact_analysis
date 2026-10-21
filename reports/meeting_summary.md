# One-page meeting summary: CBCT alginate study

Prepared: 2026-10-21

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

- The spreadsheet contains 18 site rows and 1296 numeric values: 72 per site,
  organized as 3 trials × 24 measurements. There are no blank or non-numeric measurement cells.
- 358 values (27.6%) are exactly zero. They were retained.
  Their physical/data-processing meaning still needs confirmation.
- Nine of ten manuscript scan means reproduce from trial 1 at two decimals. Scan F is 632.2047 in
  the spreadsheet (632.20) versus 632.21 in the manuscripts.
- All nine Scan A adjusted p-values reproduce as a ten-group Tukey HSD on trial 1, identifying the
  prior calculation but not validating its independence assumption.
- 8/8 anatomically matched site rows have a higher
  overall mean in the alginate scan. Descriptive differences range from
  91.6 to 529.7 gray-value
  units. These are exploratory summaries, not independent replicated effects.
- The reported E–F, G–H, and I–J p-values are not reproduced by the same Tukey procedure; the
  original method needs to be identified.

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
6. Approve the revised objective/hypothesis and supply qualitative ratings if those conclusions will
   remain in the manuscript.

## Requested meeting outcome

Approve the data dictionary, experimental unit, primary matched contrasts, role of all three trials,
and whether the current work is a descriptive pilot or has enough independent replication for a
confirmatory mixed/repeated-measures analysis.
