# Private data boundary

The source workbook is intentionally **not version-controlled**. Place it at:

```text
data/private/Alginate study master chart.xlsx
```

The repository's `.gitignore`, privacy guard, and CI check prevent Excel/raw-data formats
from being committed. The analysis pipeline writes only aggregate tables and figures to
`reports/`; it never exports the long-form, site-level measurement data.

To verify the boundary before a push:

```powershell
python scripts/privacy_guard.py --tracked
python scripts/privacy_guard.py --staged
```
