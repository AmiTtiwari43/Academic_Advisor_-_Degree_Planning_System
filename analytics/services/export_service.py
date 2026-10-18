import csv
import io
from decimal import Decimal
from typing import Any, Sequence

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value: Any) -> str:
    """
    Sanitizes a CSV cell to prevent spreadsheet formula injection attacks (CSV Injection / CWE-1236).
    If a cell value starts with '=', '+', '-', '@', horizontal tab, or carriage return,
    it is escaped by prefixing with a single quote (').
    """
    if value is None:
        return ""
    if isinstance(value, (int, float, Decimal)):
        return str(value)

    text = str(value)
    if text.startswith(FORMULA_PREFIXES):
        return f"'{text}"
    return text


def generate_report_csv(
    report_title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    max_rows: int = 5000,
) -> str:
    """
    Generates a secure, size-bounded CSV string with formula injection escaping.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header metadata row
    writer.writerow([sanitize_csv_cell(f"# Report: {report_title}")])
    writer.writerow([sanitize_csv_cell(h) for h in headers])

    # Data rows, bounded by max_rows
    for i, row in enumerate(rows):
        if i >= max_rows:
            writer.writerow(["# [TRUNCATED] Maximum row limit reached", f"Max: {max_rows}"])
            break
        writer.writerow([sanitize_csv_cell(cell) for cell in row])

    return output.getvalue()
