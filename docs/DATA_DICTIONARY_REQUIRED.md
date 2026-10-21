# Data dictionary required for analysis lock

The current workbook has no headers for 72 measurement columns. A study owner should complete and
approve the following dictionary before the dataset or statistical analysis is declared final.

## File-level metadata

| Field | Required definition |
| --- | --- |
| Dataset version | Immutable version/date and controlled storage location |
| Scanner/acquisition | Device, protocol, FOV, voxel size, kV, mA, exposure, reconstruction |
| Extraction software | Software name/version, script or procedure, export date |
| PIV units | Exact definition and valid range |
| Zero semantics | Valid observed zero, clipping/background, below-range, or missing code |
| Missing-value codes | Every allowed representation and its meaning |
| Experimental unit | Skull, scan acquisition, implant, ROI, or another unit |

## Identifier fields

| Workbook field | Current interpretation | Required confirmation |
| --- | --- | --- |
| Column A | Scan label/condition; merged across multi-site rows | Stable scan/acquisition ID and full condition |
| Column B | Implant-site code | Decode `S#`, `LB`, `LF`, `UB`, `B`, and `F` |
| Scan A | Control, no implant | Confirm skull, acquisition, and reference role |
| Scan D | Alginate; tray removed | Confirm whether alginate remained and intended contrast |

## Measurement columns

Complete one row for every numeric column C–BV. Do not infer this mapping from position alone.

| Excel range | Pipeline label | Meaning to supply |
| --- | --- | --- |
| C–Z | Trial 1, measurements 1–24 | Trial definition; radius/direction order; slice/repeat/reader |
| AA–AX | Trial 2, measurements 1–24 | Trial definition; radius/direction order; slice/repeat/reader |
| AY–BV | Trial 3, measurements 1–24 | Trial definition; radius/direction order; slice/repeat/reader |

Recommended final long-form fields:

```text
dataset_version
skull_id
scan_acquisition_id
scan_id
site_id
implant_id
alginate_status
tray_status
implant_count
anatomic_location
repeat_or_slice_id
radius_mm
direction_id
reader_or_extraction_id
piv_value
piv_unit
quality_flag
```

## Sign-off

| Role | Name | Date | Signature/approval reference |
| --- | --- | --- | --- |
| Data owner |  |  |  |
| Image-analysis owner |  |  |  |
| Statistical reviewer |  |  |  |
| Manuscript lead |  |  |  |
