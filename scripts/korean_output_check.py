#!/usr/bin/env python3
"""Flag CJK ideographs and Japanese kana in authored Korean output. Never rewrite source data."""
import argparse
import json
import re
from pathlib import Path

PATTERN=re.compile(r'[\u3040-\u30ff\u31f0-\u31ff\uff66-\uff9f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003134f]')

def inspect_text(body, allowed=()):
    # Explicit exact quotations/names only. Replacing with spaces preserves line numbers.
    for literal in allowed:
        if literal: body=body.replace(literal,''.join('\n' if c=='\n' else ' ' for c in literal))
    return [{'line':n,'characters':''.join(dict.fromkeys(PATTERN.findall(line))),'context':line[:180]}
            for n,line in enumerate(body.splitlines(),1) if PATTERN.search(line)]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('path'); p.add_argument('--allow-text',action='append',default=[])
    a=p.parse_args()
    try:
        findings=inspect_text(Path(a.path).read_text(encoding='utf-8-sig'),a.allow_text)
        print(json.dumps({'status':'문자 혼입 확인 필요' if findings else '검사 범위 내 혼입 없음',
                          'findings':findings,'limit':'언어의 의미나 자연스러움을 판별하지 않습니다. 원문·성분명·고유명사는 근거를 확인해 유지하세요.'},ensure_ascii=False,indent=2))
        return 2 if findings else 0
    except (OSError,UnicodeError) as exc:
        print(json.dumps({'status':'검사 실패','reason':str(exc)},ensure_ascii=False)); return 2

if __name__=='__main__': raise SystemExit(main())
