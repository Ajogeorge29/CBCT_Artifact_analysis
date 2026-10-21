from __future__ import annotations

from cbct_artifact_analysis.analysis import run_audit
from cbct_artifact_analysis.io import load_master_workbook


def test_audit_outputs_are_aggregate_and_complete(synthetic_workbook):
    results = run_audit(load_master_workbook(synthetic_workbook))

    assert len(results.scan_block_summary) == 10 * 3
    assert len(results.scan_overall_summary) == 10
    assert len(results.experimental_design) == 10
    assert len(results.site_descriptive_statistics) == 18
    assert results.site_descriptive_statistics["n"].eq(72).all()
    assert len(results.zero_by_scan_site_trial) == 18 * 3
    assert results.zero_by_scan_site_trial["measurement_count"].eq(24).all()
    assert len(results.matched_comparisons) == 9
    assert results.matched_comparisons["comparison"].eq("C-D").sum() == 1
    assert len(results.control_tukey_reproduction) == 9
    assert len(results.matched_pair_sensitivity) == 5 * 3
    assert len(results.matched_p_reproduction) == 3
    assert (
        results.quality_summary.loc[
            results.quality_summary["check"].eq("Missing/non-numeric values"), "result"
        ].item()
        == 0
    )
