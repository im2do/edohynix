#!/usr/bin/env python3
"""Local CSV/JSON structure and ID coverage audit. No network; never edits input."""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path


class AuditError(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuditError(f"JSON 중복 키: {key!r}; 마지막 값으로 덮어쓰지 않았습니다.")
        result[key] = value
    return result


def reject_constant(value):
    raise AuditError(f"비표준 JSON 숫자: {value}")


def load_table(path, max_bytes=20_000_000, encoding="utf-8-sig"):
    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise AuditError("크기 제한 초과. 임의 절삭하지 않았습니다. 명시적으로 나눠 검토하세요.")
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise AuditError("읽는 동안 크기 제한 초과")
    text = raw.decode(encoding, errors="strict")
    meta = {"file": path.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    suffix = path.suffix.lower()
    rows, locations, problems = [], [], []
    if suffix in (".csv", ".tsv"):
        reader = csv.reader(io.StringIO(text, newline=""), delimiter="\t" if suffix == ".tsv" else ",", strict=True)
        try:
            header = next(reader)
        except StopIteration:
            raise AuditError("헤더 없는 빈 파일")
        if not header or any(not h.strip() for h in header):
            raise AuditError("빈 열 이름")
        duplicates = [k for k, n in Counter(header).items() if n > 1]
        if duplicates:
            raise AuditError(f"중복 헤더: {duplicates}")
        previous = reader.line_num
        for index, values in enumerate(reader, 1):
            location = f"record {index}, lines {previous + 1}-{reader.line_num}"
            previous = reader.line_num
            locations.append(location)
            if len(values) != len(header):
                problems.append({"location": location, "type": "row_width", "expected": len(header), "actual": len(values)})
            rows.append(dict(zip(header, values)))
    elif suffix == ".json":
        data = json.loads(text, object_pairs_hook=unique_object, parse_float=Decimal, parse_constant=reject_constant)
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise AuditError("JSON 최상위는 객체의 배열이어야 합니다. 다른 구조를 자동 추정하지 않습니다.")
        rows = data
        locations = [f"JSON /{i}" for i in range(len(rows))]
    else:
        raise AuditError("CSV/TSV/JSON만 지원. PDF/OCR은 별도 원문 확인이 필요합니다.")
    return {"meta": meta, "rows": rows, "locations": locations, "problems": problems}


def id_key(value):
    if isinstance(value, (dict, list, bool)) or value is None:
        raise AuditError("ID는 문자열 또는 유한 숫자여야 합니다.")
    if isinstance(value, str) and not value.strip():
        raise AuditError("빈 ID")
    return f"{type(value).__name__}:{value}"


def audit_table(table, id_column, required=()):
    issues = list(table["problems"])
    ids = {}
    counts = {"missing_fields": 0, "null_values": 0, "blank_values": 0}
    required_columns = tuple(dict.fromkeys([id_column, *required]))
    for row, loc in zip(table["rows"], table["locations"]):
        for col in required_columns:
            if col not in row:
                kind = "missing_fields"
            elif row[col] is None:
                kind = "null_values"
            elif isinstance(row[col], str) and not row[col].strip():
                kind = "blank_values"
            else:
                continue
            counts[kind] += 1
            issues.append({"location": loc, "column": col, "type": kind})
        if id_column in row:
            try:
                key = id_key(row[id_column])
                ids.setdefault(key, []).append(loc)
            except AuditError as exc:
                issues.append({"location": loc, "column": id_column, "type": "invalid_id", "detail": str(exc)})
    duplicates = [{"id": k, "count": len(v), "locations": v} for k, v in ids.items() if len(v) > 1]
    report = {
        **table["meta"], "scope": "구조·명시한 필수열·ID 검증. 업무 적합 판정 아님.",
        "records_total": len(table["rows"]), "records_checked": len(table["rows"]),
        "unique_ids": len(ids), "id_column": id_column, "required_columns": list(required_columns),
        "field_issues": counts, "duplicate_ids": duplicates, "issues": issues,
        "status": "확인 필요" if issues or duplicates else "구조 검사 통과", "id_locations": ids,
    }
    return report


def compare_coverage(actual, expected):
    left = Counter({k: len(v) for k, v in expected["id_locations"].items()})
    right = Counter({k: len(v) for k, v in actual["id_locations"].items()})
    difference = [{"id": key, "expected": left[key], "actual": right[key]} for key in sorted(left.keys() | right.keys()) if left[key] != right[key]]
    valid_inputs = actual["status"] == expected["status"] == "구조 검사 통과"
    return {"expected_file": expected["file"], "expected_status": expected["status"], "differences": difference,
            "status": "ID 커버리지 통과" if valid_inputs and not difference else "확인 필요",
            "limit": "필터·일대다 결합의 적법성 및 다른 열 값은 검사하지 않음. ID는 타입까지 비교."}


def dump_new(report, output=None):
    body = json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n"
    if output:
        with Path(output).open("x", encoding="utf-8") as stream:
            stream.write(body)
    else:
        print(body, end="")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--id", required=True, dest="id_column")
    parser.add_argument("--required", nargs="*", default=[])
    parser.add_argument("--expected", help="결과 ID와 대조할 원본 표. 같은 ID 열 필요.")
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--max-bytes", type=int, default=20_000_000)
    parser.add_argument("--out", help="새 JSON 파일. 기존 파일은 덮어쓰지 않음.")
    args = parser.parse_args()
    try:
        report = audit_table(load_table(args.input, args.max_bytes, args.encoding), args.id_column, args.required)
        if args.expected:
            baseline = audit_table(load_table(args.expected, args.max_bytes, args.encoding), args.id_column)
            report["coverage"] = compare_coverage(report, baseline)
        dump_new(report, args.out)
        return 0 if report["status"] == "구조 검사 통과" and report.get("coverage", {}).get("status", "ID 커버리지 통과") == "ID 커버리지 통과" else 2
    except (AuditError, OSError, UnicodeError, csv.Error, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "실행 불가", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
