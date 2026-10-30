#!/usr/bin/env python3
"""Check requirement-to-verification traceability, not business truth or test execution."""
import argparse
import json
from pathlib import Path
from data_audit import unique_object, reject_constant


def read_object(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique_object, parse_constant=reject_constant)


def contained(workspace, relative):
    workspace = Path(workspace).resolve()
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError("기록 경로는 작업 폴더 내부 상대경로여야 합니다.")
    p = (workspace / relative).resolve()
    if not p.is_relative_to(workspace):
        raise ValueError("작업 폴더 밖 기록은 읽지 않습니다.")
    return p


def evaluate(requirements, checks, stage):
    issues, warnings = [], []
    if not isinstance(requirements, list) or not isinstance(checks, list):
        raise ValueError("requirements와 checks는 배열이어야 합니다.")
    if not requirements:
        issues.append("요구사항이 비어 있습니다.")
    ids = set()
    for req in requirements:
        if not isinstance(req, dict) or not isinstance(req.get('id'), str) or not req['id'].strip():
            issues.append("유효한 요구 ID가 없습니다."); continue
        rid = req['id']
        if rid in ids:
            issues.append(f"{rid}: 요구 ID 중복")
        ids.add(rid)
        if req.get('status') not in ('confirmed', 'proposed', 'unresolved'):
            issues.append(f"{rid}: 상태는 confirmed/proposed/unresolved")
        if type(req.get('required')) is not bool:
            issues.append(f"{rid}: 필수 여부 required는 true/false로 명시")
        for field in ('requirement', 'criterion'):
            if not isinstance(req.get(field), str) or not req[field].strip():
                issues.append(f"{rid}: {field} 없음")
        source = req.get('source')
        if req.get('status') == 'confirmed' and (not isinstance(source, dict) or not source.get('kind') or not source.get('ref')):
            issues.append(f"{rid}: 확정 조건의 근거 위치 없음")
        if req.get('status') != 'confirmed':
            message = f"{rid}: 아직 확정되지 않은 요구"
            (issues if req.get('required') and stage == 'deliver' else warnings).append(message)
    check_ids, passed, failed, not_run = set(), set(), set(), set()
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get('id'), str) or not check['id'].strip():
            issues.append("유효한 검사 ID가 없습니다."); continue
        cid = check['id']
        if cid in check_ids:
            issues.append(f"{cid}: 검사 ID 중복")
        check_ids.add(cid)
        refs = check.get('requirements')
        if not isinstance(refs, list) or not refs or any(not isinstance(x, str) for x in refs):
            issues.append(f"{cid}: 연결한 요구 ID 배열 없음"); continue
        for rid in refs:
            if rid not in ids:
                issues.append(f"{cid}: 없는 요구 {rid}에 연결됨")
        state = check.get('status')
        if state not in ('pass', 'fail', 'not_run'):
            issues.append(f"{cid}: 검사 상태 오류")
        if state == 'not_run':
            not_run.update(refs)
        if not check.get('expected'):
            issues.append(f"{cid}: 독립 기대 결과 없음")
        if state in ('pass', 'fail'):
            if not check.get('actual') or not check.get('evidence'):
                issues.append(f"{cid}: 실제 결과 또는 증거 위치 없음")
            elif state == 'pass':
                passed.update(refs)
            else:
                failed.update(refs)
    if stage == 'build' and not any(isinstance(x, dict) and x.get('status') == 'confirmed' for x in requirements):
        issues.append("구현할 확정 요구가 없습니다.")
    if stage == 'deliver':
        for req in requirements:
            if not isinstance(req, dict) or not req.get('required'):
                continue
            rid = req.get('id')
            if rid not in passed:
                issues.append(f"{rid}: 필수 요구의 통과 근거 없음")
            if rid in failed:
                issues.append(f"{rid}: 실패 검사 남음")
            if rid in not_run:
                issues.append(f"{rid}: 필수 요구에 연결된 미실행 검사 남음")
    return {"stage": stage, "status": "기록 연결 통과" if not issues else "확인 필요", "issues": issues,
            "warnings": warnings, "requirements": len(requirements), "checks": len(checks),
            "limit": "원문 해석·기대값 정확성·로그 내용·테스트 최신성은 이 검사만으로 증명되지 않습니다."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--stage', choices=['discover', 'build', 'deliver'], required=True)
    args = parser.parse_args()
    try:
        workspace = Path(args.workspace).resolve()
        config = read_object(workspace / 'FDE_HARNESS.json')
        if config.get('progress'):
            from fde_state import assess
            state = read_object(contained(workspace, config['progress']))
            report = assess(state, workspace)
            if args.stage == 'build':
                from review_guards import open_conflicts
                issues = [] if any(r['status'] == 'confirmed' and not open_conflicts(r) for r in state['requirements']) else ['충돌 없이 구현할 확정 요구 없음']
            elif args.stage == 'deliver':
                issues = report['delivery_issues']
            else:
                issues = [] if state.get('goal') and state['requirements'] else ['목표/요구 기록 없음']
            result = {'stage':args.stage, 'status':'확인 필요' if issues else '기록 연결 통과',
                      'issues':issues, 'progress':report}
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 2 if issues else 0
        requirements = read_object(contained(workspace, config['requirements']))['requirements']
        checks = read_object(contained(workspace, config['verification']))['checks']
        result = evaluate(requirements, checks, args.stage)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == '기록 연결 통과' else 2
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status":"검사 중단","reason":str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
