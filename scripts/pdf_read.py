#!/usr/bin/env python3
"""Local, page-indexed PDF extraction. No network, implicit installs or OCR claims."""
import argparse
import hashlib
import importlib.util
import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path


def capabilities():
    return {'pypdf': bool(importlib.util.find_spec('pypdf')),
            'poppler': bool(shutil.which('pdfinfo') and shutil.which('pdftotext')),
            'pdfplumber': bool(importlib.util.find_spec('pdfplumber')),
            'pdfkit': platform.system() == 'Darwin' and bool(shutil.which('swift'))}


def selected_pages(spec, count):
    if not spec:
        return list(range(1, count + 1))
    result = set()
    for part in spec.split(','):
        bounds = part.strip().split('-')
        if len(bounds) not in (1, 2):
            raise ValueError('페이지 형식: 1-3,5')
        start = int(bounds[0]); end = int(bounds[-1])
        if not 1 <= start <= end <= count:
            raise ValueError(f'페이지 범위는 1~{count}입니다.')
        result.update(range(start, end + 1))
    return sorted(result)


def run(args, timeout):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout).stdout


def extract(path, engine='auto', pages=None, timeout=120):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('입력 PDF가 없습니다.')
    available = capabilities()
    choices = [k for k, enabled in available.items() if enabled] if engine == 'auto' else [engine]
    if not choices:
        raise ValueError('추출 도구 없음. --doctor로 확인하고 pypdf 또는 Poppler를 준비하세요.')
    errors = []
    for backend in choices:
        try:
            if not available.get(backend):
                raise ValueError(f'{backend} 도구가 없습니다.')
            opened = None
            if backend == 'pypdf':
                from pypdf import PdfReader
                opened = PdfReader(str(path))
                if opened.is_encrypted and not opened.decrypt(''):
                    raise ValueError('암호가 필요한 PDF입니다. 우회하지 않습니다.')
                count = len(opened.pages)
            elif backend == 'pdfplumber':
                import pdfplumber
                opened = pdfplumber.open(path)
                count = len(opened.pages)
            elif backend == 'poppler':
                info = run(['pdfinfo', str(path)], timeout)
                count = next(int(x.split(':', 1)[1]) for x in info.splitlines() if x.startswith('Pages:'))
            else:
                helper = Path(__file__).with_name('pdfkit_extract.swift')
                # Do not require permission to write the user's global Swift/Clang cache.
                with tempfile.TemporaryDirectory(prefix='fde-pdfkit-') as cache:
                    result = json.loads(run(['swift', '-module-cache-path', cache, str(helper), str(path)], timeout))
                count = result['page_count']
            indexes = selected_pages(pages, count)
            records = []
            try:
                for number in indexes:
                    try:
                        if backend == 'pypdf':
                            text = opened.pages[number - 1].extract_text() or ''
                        elif backend == 'pdfplumber':
                            text = opened.pages[number - 1].extract_text(layout=True) or ''
                        elif backend == 'poppler':
                            text = run(['pdftotext', '-layout', '-enc', 'UTF-8', '-f', str(number),
                                        '-l', str(number), str(path), '-'], timeout).replace('\f', '')
                        else:
                            text = result['pages'][number - 1]['text']
                        sparse = len(''.join(text.split())) < 20
                        records.append({'page': number, 'text': text, 'characters': len(text),
                                        'status': 'needs_visual_check' if sparse else 'text_extracted',
                                        'warning': '텍스트 희소/없음. 스캔·도식·폰트 문제 가능. 값 없음으로 해석 금지.' if sparse else None})
                    except Exception as exc:
                        records.append({'page': number, 'text': '', 'characters': 0,
                                        'status': 'extraction_failed', 'warning': str(exc)[:300]})
            finally:
                if backend == 'pdfplumber' and opened:
                    opened.close()
            return {'file': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'engine': backend, 'page_count': count, 'selected_pages': indexes, 'pages': records,
                    'backend_errors': errors, 'ocr_performed': False,
                    'table_layout_verified': False,
                    'limit': '비어 있지 않은 추출문도 표 열·단위·각주·그림이 정확하다는 증거는 아닙니다.'}
        except Exception as exc:
            message = str(exc)
            if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
                message += ' ' + exc.stderr.strip()[-700:]
            errors.append({'engine': backend, 'error': message[:1000]})
            if engine != 'auto':
                break
    raise ValueError('추출 실패: ' + json.dumps(errors, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pdf', nargs='?')
    p.add_argument('--doctor', action='store_true')
    p.add_argument('--engine', choices=['auto', 'pypdf', 'poppler', 'pdfplumber', 'pdfkit'], default='auto')
    p.add_argument('--pages')
    p.add_argument('--output', help='새 JSON 파일. 기존 파일을 덮지 않습니다.')
    p.add_argument('--timeout', type=int, default=120)
    a = p.parse_args()
    try:
        if a.doctor:
            print(json.dumps({'capabilities': capabilities(), 'network_used': False}, ensure_ascii=False)); return 0
        if not a.pdf or not a.output:
            raise ValueError('입력 PDF와 --output을 지정하세요. 먼저 --doctor 사용 가능.')
        output = Path(a.output)
        if output.exists() or output.is_symlink():
            raise ValueError('출력 파일이 이미 있습니다. 새 이름을 사용하세요.')
        result = extract(a.pdf, a.engine, a.pages, a.timeout)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        pending = [r['page'] for r in result['pages'] if r['status'] != 'text_extracted']
        print(json.dumps({'output': str(output), 'engine': result['engine'], 'total_pages': result['page_count'],
                          'extracted_pages': len(result['pages']), 'visual_check_pages': pending,
                          'table_layout_verified': False}, ensure_ascii=False))
        return 2 if pending else 0
    except (ValueError, OSError) as exc:
        print(json.dumps({'status': '확인 필요', 'reason': str(exc)}, ensure_ascii=False)); return 2


if __name__ == '__main__':
    raise SystemExit(main())
