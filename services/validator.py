import csv
import io
import re
from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning"
    file: str
    row: int | None
    column: str | None
    message: str


@dataclass
class ValidationResult:
    passed: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, severity: str, file: str, message: str, row: int | None = None, column: str | None = None):
        self.issues.append(ValidationIssue(severity, file, row, column, message))
        if severity == "error":
            self.passed = False

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "error_count": sum(1 for i in self.issues if i.severity == "error"),
            "warning_count": sum(1 for i in self.issues if i.severity == "warning"),
            "issues": [
                {"severity": i.severity, "file": i.file, "row": i.row, "column": i.column, "message": i.message}
                for i in self.issues
            ],
        }


def validate_csv_sections(sections: list[dict]) -> ValidationResult:
    result = ValidationResult()

    for section in sections:
        name = section["name"]
        content = section["content"]
        _validate_csv_structure(result, name, content)
        _validate_empty_values(result, name, content)
        _validate_date_columns(result, name, content)
        _validate_numeric_columns(result, name, content)

    if len(sections) == 2:
        _validate_cross_file_keys(result, sections)

    return result


def _validate_csv_structure(result: ValidationResult, name: str, content: str):
    lines = content.strip().splitlines()
    if len(lines) < 2:
        result.add("error", name, "File has no data rows (only header or empty)")
        return

    reader = csv.reader(io.StringIO(content.strip()))
    rows = list(reader)
    header_count = len(rows[0])

    for i, row in enumerate(rows[1:], start=2):
        if len(row) != header_count:
            result.add("error", name, f"Column count mismatch: expected {header_count}, got {len(row)}", row=i)


def _validate_empty_values(result: ValidationResult, name: str, content: str):
    reader = csv.DictReader(io.StringIO(content.strip()))
    for i, row in enumerate(reader, start=2):
        for col, val in row.items():
            if val is None or val.strip() == "":
                result.add("warning", name, "Empty value", row=i, column=col)


def _validate_date_columns(result: ValidationResult, name: str, content: str):
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    reader = csv.DictReader(io.StringIO(content.strip()))

    date_cols = [c for c in (reader.fieldnames or []) if "DATE" in c.upper()]
    if not date_cols:
        return

    reader = csv.DictReader(io.StringIO(content.strip()))
    for i, row in enumerate(reader, start=2):
        for col in date_cols:
            val = row.get(col, "").strip()
            if val and not date_pattern.match(val):
                result.add("error", name, f"Invalid date format '{val}', expected YYYY-MM-DD", row=i, column=col)


def _validate_numeric_columns(result: ValidationResult, name: str, content: str):
    reader = csv.DictReader(io.StringIO(content.strip()))
    numeric_cols = [c for c in (reader.fieldnames or []) if any(k in c.upper() for k in ["AMOUNT", "AMT", "PRICE", "TOTAL", "NUMBER"])]

    if not numeric_cols:
        return

    reader = csv.DictReader(io.StringIO(content.strip()))
    for i, row in enumerate(reader, start=2):
        for col in numeric_cols:
            val = row.get(col, "").strip()
            if not val:
                continue
            try:
                float(val)
            except ValueError:
                result.add("error", name, f"Non-numeric value '{val}'", row=i, column=col)


def _validate_cross_file_keys(result: ValidationResult, sections: list[dict]):
    header_reader = csv.DictReader(io.StringIO(sections[0]["content"].strip()))
    lines_reader = csv.DictReader(io.StringIO(sections[1]["content"].strip()))

    header_fields = header_reader.fieldnames or []
    lines_fields = lines_reader.fieldnames or []

    common_keys = set(header_fields) & set(lines_fields)
    if not common_keys:
        return

    key_col = sorted(common_keys)[0]

    header_keys = set()
    for row in header_reader:
        val = row.get(key_col, "").strip()
        if val:
            header_keys.add(val)

    for i, row in enumerate(lines_reader, start=2):
        val = row.get(key_col, "").strip()
        if val and val not in header_keys:
            result.add("error", sections[1]["name"], f"Key '{val}' not found in header file", row=i, column=key_col)

    header_reader2 = csv.DictReader(io.StringIO(sections[0]["content"].strip()))
    header_keys_list = [row.get(key_col, "").strip() for row in header_reader2]
    seen = set()
    for i, k in enumerate(header_keys_list, start=2):
        if k in seen:
            result.add("error", sections[0]["name"], f"Duplicate key '{k}'", row=i, column=key_col)
        seen.add(k)
