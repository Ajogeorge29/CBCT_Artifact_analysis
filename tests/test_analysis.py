from __future__ import annotations

from cbct_artifact_analysis.analysis import run_audit
from cbct_artifact_analysis.io import load_master_workbook


def test_audit_outputs_are_aggregate_and_complete(synthetic_workbook):
    results = run_audit(load_master_workbook(synthetic_workbook))

    assert len(results.scan_block_summary) == 10 * 3
    assert len(results.scan_overall_summary) == 10
    assert len(results.control_tukey_reproduction) == 9
    assert len(results.matched_pair_sensitivity) == 5 * 3
    assert len(results.matched_p_reproduction) == 3
    assert (
        results.quality_summary.loc[
            results.quality_summary["check"].eq("Missing/non-numeric values"), "result"
        ].item()
        == 0
    )
