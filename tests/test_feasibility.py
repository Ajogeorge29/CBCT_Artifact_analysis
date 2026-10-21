from __future__ import annotations

from cbct_artifact_analysis.feasibility import (
    GROUP_ORDER,
    _binary_features,
    _prepare_model_frame,
    _rule_predictions,
)
from cbct_artifact_analysis.io import load_master_workbook


def test_feasibility_features_and_groups_do_not_use_scan_id(synthetic_workbook):
    frame = _prepare_model_frame(load_master_workbook(synthetic_workbook).long)
    design, design_names = _binary_features(frame, include_position=False)
    positioned, positioned_names = _binary_features(frame, include_position=True)

    assert set(frame["configuration_group"]) == set(GROUP_ORDER)
    assert all("scan_id" not in name for name in positioned_names)
    assert len(positioned_names) == len(set(positioned_names))
    assert positioned.shape[1] == design.shape[1] + 24
    assert len(design_names) == design.shape[1]


def test_rule_baseline_uses_training_rows_only(synthetic_workbook):
    frame = _prepare_model_frame(load_master_workbook(synthetic_workbook).long)
    held_out = frame["configuration_group"].eq("control_no_implant")
    predictions = _rule_predictions(
        frame.loc[~held_out], frame.loc[held_out], include_position=True
    )

    assert len(predictions) == int(held_out.sum())
    assert all(value == value for value in predictions)
