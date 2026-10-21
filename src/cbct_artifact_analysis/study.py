"""Study metadata stated in the manuscripts.

The workbook itself has no header row or data dictionary. These labels are kept in one
place so that assumptions are explicit and reviewable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScanMetadata:
    scan_id: str
    condition: str
    alginate: bool
    implant_count: int
    description: str


SCAN_METADATA = {
    "A": ScanMetadata("A", "Control: no implant", False, 0, "Control without implant"),
    "B": ScanMetadata("B", "No alginate", False, 1, "Posterior mandible"),
    "C": ScanMetadata("C", "Alginate", True, 1, "Posterior mandible; tray present"),
    "D": ScanMetadata(
        "D",
        "Alginate; tray removed",
        True,
        1,
        "Posterior mandible; manuscript labels alginate present and tray removed",
    ),
    "E": ScanMetadata("E", "No alginate", False, 2, "Contralateral posterior arches"),
    "F": ScanMetadata("F", "Alginate", True, 2, "Contralateral posterior arches"),
    "G": ScanMetadata("G", "No alginate", False, 2, "Mandibular anterior and posterior"),
    "H": ScanMetadata("H", "Alginate", True, 2, "Mandibular anterior and posterior"),
    "I": ScanMetadata("I", "No alginate", False, 3, "Three implant locations"),
    "J": ScanMetadata("J", "Alginate", True, 3, "Three implant locations"),
}

# Like-for-like configurations identified in the manuscript. C-D is a tray comparison,
# not an alginate/no-alginate contrast.
MATCHED_PAIRS = {
    "B-C": ("B", "C", "1 implant"),
    "E-F": ("E", "F", "2 implants, contralateral arches"),
    "G-H": ("G", "H", "2 implants, same jaw"),
    "I-J": ("I", "J", "3 implants"),
}

TRAY_PAIR = {"C-D": ("C", "D", "Alginate with tray vs tray removed")}

# Values printed in both source documents. They are aggregate publication values and are safe to
# include in the reproducibility check. Scan F differs from the audited workbook by 0.0053.
MANUSCRIPT_SCAN_MEANS = {
    "A": 123.05,
    "B": 395.84,
    "C": 534.36,
    "D": 589.17,
    "E": 261.09,
    "F": 632.21,
    "G": 465.33,
    "H": 598.67,
    "I": 372.97,
    "J": 639.13,
}

# Adjusted p-values printed for Scan A comparisons. The analysis shows that these reproduce
# from a ten-group Tukey HSD applied to block 1 measurements.
MANUSCRIPT_CONTROL_P = {
    "B": 0.622,
    "C": 0.091,
    "D": 0.029,
    "E": 0.979,
    "F": 0.001,
    "G": 0.123,
    "H": 0.003,
    "I": 0.453,
    "J": 0.000,
}

# The manuscript does not identify the statistical method used for this second table.
MANUSCRIPT_MATCHED_P = {"E-F": 0.012, "G-H": 0.087, "I-J": 0.049}

EXPECTED_SITE_COUNTS = {
    "A": 1,
    "B": 1,
    "C": 1,
    "D": 1,
    "E": 2,
    "F": 2,
    "G": 2,
    "H": 2,
    "I": 3,
    "J": 3,
}
