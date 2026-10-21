# Statistical limitations

## Repeated points are not independent samples

Each site row contains 72 gray values: 24 sampling locations in each of three trials. Measurements
from the same image volume share the same skull, implant configuration, acquisition, reconstruction,
and much of the same local anatomy. They are correlated technical measurements. Counting every point
as an independent experimental replicate inflates the apparent sample size and can make standard
errors, confidence intervals, and p-values too optimistic. Multiplicity correction such as Tukey HSD
does not repair this independence problem.

The experimental unit must be identified before confirmatory inference. If multiple independently
prepared skulls or independently repeated scan acquisitions exist, a hierarchical model could place
points within trial, site/implant, scan, and skull as supported by the design. If there is only one
acquisition for each condition, the current results should be presented as descriptive/exploratory;
independent scan-level replication is needed for population-level claims.

The exploratory paired analysis aggregates the 24 points within each trial before comparing B–C,
E–F, G–H, I–J, and C–D. This avoids counting the individual points as independent pairs, but it
leaves only three trial pairs per comparison. An exact two-sided sign-flip test cannot produce a
p-value below 0.25 with three same-direction pairs. In addition, the trials may be repeated
extractions from the same acquisition rather than independent acquisitions, so even that p-value
must not be treated as confirmatory evidence.

## Other limitations

- Scan A has no implant. Its contrast with implant scans cannot isolate an alginate effect.
- Implant number and anatomical location change across scan IDs. Primary interpretation should use
  the matched B–C, E–F, G–H, and I–J configurations; C–D is a separate tray comparison.
- The three trials are identified by spreadsheet position, but their acquisition/extraction meaning
  and the order of radius/direction measurements still need documentation.
- Exact zeros constitute 27.6% of values. They were retained, but their physical or processing
  meaning is unknown.
- Trial 1 was used for manuscript means and reported Scan A p-values; the omission of trials 2–3
  needs a documented rationale or a repeated-measures sensitivity analysis.
- The qualitative Likert ratings and reader IDs are absent, preventing inter-rater analysis.
- Predictive validation is limited to five scan-configuration families. Grouped RTM and linear
  regression errors describe this dataset only; they are not clinical generalization estimates.
