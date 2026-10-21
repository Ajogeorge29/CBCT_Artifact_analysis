# Analysis decisions and audit trail

This document separates facts visible in the source materials from assumptions introduced by the
reproducibility pipeline. Update it whenever a study owner resolves an open question.

## Confirmed from the workbook and manuscripts

- The workbook has one worksheet and no header row.
- Rows 1–18 contain implant-site data; later non-empty rows are analysis notes.
- Column A identifies scans, and merged cells span scans with multiple implant sites.
- Column B contains 18 unique site codes.
- Columns C–BV contain 72 numeric values per site, organized as three 24-measurement trial blocks.
- The manuscript states that eight points were sampled at each of three radii (0.5, 1, and 2 mm),
  implying 24 PIV observations per implant site.
- Scan A is a no-implant control. Scans B/E/G/I are described as no alginate. Scans C/D/F/H/J are
  described as alginate, with Scan D's tray removed.
- Nine of the manuscript's ten scan means match the mean of workbook columns C–Z (the first 24
  values) to two decimals. Scan F is 632.2047 in the workbook (632.20 at two decimals) but 632.21
  in both manuscripts; all ten absolute discrepancies are below 0.006.
- The Scan A adjusted p-values match a Tukey HSD across all ten scan-ID groups using those same
  first 24 values.

## Explicit pipeline conventions

- Columns C–Z are `trial 1`, AA–AX `trial 2`, and AY–BV `trial 3`.
- Within each trial, columns are numbered `measurement 1` through `measurement 24`.
- The pipeline does **not** assign radius, direction, slice, repeat, or observer labels because the
  source file does not justify them.
- Merged scan labels are carried forward only across rows whose column-B value matches a site code.
- Zero is retained as a numeric value. It is not converted to missingness without a study-owner
  definition.
- All row-level values remain memory-only. Reports and tables contain aggregates.
- The existing Tukey calculation is reproduced for audit purposes, not endorsed as the final
  inferential model.

## Open decisions blocking a final analysis

1. What acquisition, slice, or extraction procedure operationally defines a trial?
2. What is the exact order of radius and spatial direction inside each 24-value trial?
3. Why did the manuscripts use trial 1 and omit trials 2–3?
4. What does an exact zero mean in the source extraction?
5. How many independent skulls, scan acquisitions, implant placements, and repeat extractions were
   performed? Which workbook fields identify them?
6. Were the same ROIs/points paired across matched scans, and is there a stable point identifier?
7. What software and procedure produced the E–F, G–H, and I–J p-values of 0.012, 0.087, and 0.049?
8. For Scan D, was alginate still in contact with the skull after the tray was removed? How should
   this condition be named analytically?
9. Where are the two radiologists' qualitative Likert ratings and reader identifiers?
10. Are PIV values in scanner gray values, normalized units, or another scale?

## Proposed analysis after clarification

The final model must follow the actual replication structure. If independent skulls/scans exist,
use a hierarchical or repeated-measures model with the alginate contrast pre-specified and technical
PIV readings nested at their true levels. If there is only one acquisition per scan configuration,
report effect estimates and sensitivity analyses descriptively and treat inferential p-values as
exploratory. Do not manufacture an independent sample size from multiple points within one scan.
