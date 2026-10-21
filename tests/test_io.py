from __future__ import annotations

from cbct_artifact_analysis.io import load_master_workbook


def test_headerless_workbook_is_reshaped_without_exporting_rows(synthetic_workbook):
    data = load_master_workbook(synthetic_workbook)

    assert data.profile.data_rows == 18
    assert data.profile.note_rows == 1
    assert len(data.long) == 18 * 72
    assert data.long["scan_id"].nunique() == 10
    assert data.long.groupby("site_code").size().eq(72).all()
    assert set(data.long["block"]) == {1, 2, 3}
    assert set(data.long["measurement"]) == set(range(1, 25))


def test_block_boundaries_are_deterministic(synthetic_workbook):
    data = load_master_workbook(synthetic_workbook)
    first_site = data.long.loc[data.long["site_code"].eq("S1LB")]

    assert first_site.loc[first_site["block"].eq(1), "value"].tolist() == [
        float(1000 + offset) for offset in range(24)
    ]
    assert first_site.loc[first_site["block"].eq(2), "value"].tolist() == [
        float(1024 + offset) for offset in range(24)
    ]
    assert first_site.loc[first_site["block"].eq(3), "value"].tolist() == [
        float(1048 + offset) for offset in range(24)
    ]
