#!/usr/bin/env python3
"""Verified token mapping only; does not perform OCR or Hangul key decomposition."""
import argparse
import json
from pathlib import Path
from data_audit import AuditError, dump_new, reject_constant, unique_object


def strict_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object, parse_constant=reject_constant)


def transform(pairs, tokens, reverse=False):
    if not isinstance(pairs, list) or not isinstance(tokens, list) or any(not isinstance(t, str) or not t for t in tokens):
        raise AuditError("매핑은 쌍 배열, 입력은 빈 값 없는 문자열 토큰 배열이어야 합니다.")
    forward, inverse = {}, {}
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2 or any(not isinstance(t, str) or not t for t in pair):
            raise AuditError("매핑의 각 행은 빈 값 없는 [원본토큰, 대상토큰]이어야 합니다.")
        a, b = pair
        if a in forward or b in inverse:
            raise AuditError("중복 원본/대상으로 일대일 매핑이 아닙니다. 임의 역변환하지 않습니다.")
        forward[a], inverse[b] = b, a
    lookup, undo = (inverse, forward) if reverse else (forward, inverse)
    trace = [{"position": i + 1, "input": t, "output": lookup.get(t), "status": "확인" if t in lookup else "매핑 없음"} for i, t in enumerate(tokens)]
    output = [row["output"] for row in trace]
    known = all(t is not None for t in output)
    roundtrip = [undo[t] for t in output] == tokens if known else None
    return {"direction": "역방향" if reverse else "정방향", "input_count": len(tokens), "output_count": len(output),
            "trace": trace, "output_tokens": output, "roundtrip": roundtrip,
            "status": "매핑 검사 통과" if known and roundtrip else "확인 필요",
            "limit": "제공된 매핑표의 의미·방향은 사람이 원문 대조. 한글 분해·재조합은 별도."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping")
    parser.add_argument("tokens")
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args()
    try:
        report = transform(strict_json(args.mapping), strict_json(args.tokens), args.reverse)
        dump_new(report, args.out)
        return 0 if report["status"] == "매핑 검사 통과" else 2
    except (AuditError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "실행 불가", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
