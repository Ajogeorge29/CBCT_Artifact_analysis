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
    anatomical_site: str
    tray_status: str
    description: str


SCAN_METADATA = {
    "A": ScanMetadata(
        "A",
        "Control: no implant",
        False,
        0,
        "Posterior mandible measurement site; no implant",
        "None",
        "No-implant control",
    ),
    "B": ScanMetadata(
        "B",
        "No alginate",
        False,
        1,
        "Posterior mandible",
        "None",
        "One posterior mandibular implant",
    ),
    "C": ScanMetadata(
        "C",
        "Alginate",
        True,
        1,
        "Posterior mandible",
        "Present during acquisition",
        "One posterior mandibular implant",
    ),
    "D": ScanMetadata(
        "D",
        "Alginate; tray removed",
        True,
        1,
        "Posterior mandible",
        "Removed before acquisition",
        "Manuscript labels alginate present; confirm what remained after tray removal",
    ),
    "E": ScanMetadata(
        "E",
        "No alginate",
        False,
        2,
        "Mandibular posterior + maxillary posterior (same side)",
        "None",
        "Two implants in opposing arches",
    ),
    "F": ScanMetadata(
        "F",
        "Alginate",
        True,
        2,
        "Mandibular posterior + maxillary posterior (same side)",
        "Present during acquisition",
        "Two implants in opposing arches",
    ),
    "G": ScanMetadata(
        "G",
        "No alginate",
        False,
        2,
        "Mandibular anterior + mandibular posterior",
        "None",
        "Two implants in the same jaw",
    ),
    "H": ScanMetadata(
        "H",
        "Alginate",
        True,
        2,
        "Mandibular anterior + mandibular posterior",
        "Present during acquisition",
        "Two implants in the same jaw",
    ),
    "I": ScanMetadata(
        "I",
        "No alginate",
        False,
        3,
        "Mandibular anterior + mandibular posterior + maxillary posterior",
        "None",
        "Three implant locations",
    ),
    "J": ScanMetadata(
        "J",
        "Alginate",
        True,
        3,
        "Mandibular anterior + mandibular posterior + maxillary posterior",
        "Present during acquisition",
        "Three implant locations",
    ),
}

SITE_ANATOMY = {
    "S1LB": "Posterior mandible (no-implant control)",
    "S2LB": "Posterior mandible",
    "S3LB": "Posterior mandible",
    "S4LB": "Posterior mandible",
    "S5LB": "Mandibular posterior",
    "S5UB": "Maxillary posterior",
    "S10LB": "Mandibular posterior",
    "S10UB": "Maxillary posterior",
    "S6LB": "Mandibular posterior",
    "S6LF": "Mandibular anterior",
    "S7B": "Mandibular posterior",
    "S7F": "Mandibular anterior",
    "S8LB": "Mandibular posterior",
    "S8LF": "Mandibular anterior",
    "S8UB": "Maxillary posterior",
    "S9LB": "Mandibular posterior",
    "S9LF": "Mandibular anterior",
    "S9UB": "Maxillary posterior",
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

# Site-level pairings used for the professor-requested matched plot and table. These compare the
# same anatomical component within each scan configuration. C-D is intentionally separate because
# both scans are labelled as containing alginate.
MATCHED_SITE_PAIRS = [
    ("B-C", "S2LB", "S3LB", "Posterior mandible; 1 implant"),
    ("E-F", "S5LB", "S10LB", "Mandibular posterior; 2 implants/opposing arches"),
    ("E-F", "S5UB", "S10UB", "Maxillary posterior; 2 implants/opposing arches"),
    ("G-H", "S6LB", "S7B", "Mandibular posterior; 2 implants/same jaw"),
    ("G-H", "S6LF", "S7F", "Mandibular anterior; 2 implants/same jaw"),
    ("I-J", "S8LB", "S9LB", "Mandibular posterior; 3 implants"),
    ("I-J", "S8LF", "S9LF", "Mandibular anterior; 3 implants"),
    ("I-J", "S8UB", "S9UB", "Maxillary posterior; 3 implants"),
]

TRAY_SITE_PAIR = ("C-D", "S3LB", "S4LB", "Posterior mandible; tray present vs removed")

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
# from a ten-group Tukey HSD applied to trial 1 measurements.
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
