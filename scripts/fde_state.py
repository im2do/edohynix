#!/usr/bin/env python3
"""Durable requirement ledger. A log is evidence of recording, not proof of business truth."""
import argparse
import copy
import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from check_handoff import contained, read_object
from review_guards import validate_policy, validate_transition, open_conflicts


def stamp(): return datetime.now(timezone.utc).isoformat()


def state_path(workspace):
    workspace = Path(workspace).resolve()
    config = workspace / 'FDE_HARNESS.json'
    rel = read_object(config).get('progress', 'FDE_PROGRESS.json') if config.exists() else 'FDE_PROGRESS.json'
    return contained(workspace, rel)


def initial():
    return {'schema_version': 1, 'revision': 0, 'goal': None, 'requirements': [],
            'checks': [], 'artifacts': [], 'history': []}


def atomic_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
            temp = Path(f.name)
            json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp and temp.exists(): temp.unlink()


def require_text(value, label):
    if not isinstance(value, str) or not value.strip(): raise ValueError(label + ' 필요')


def source_ok(value):
    if not isinstance(value, dict): raise ValueError('source 객체 필요')
    require_text(value.get('kind'), 'source.kind'); require_text(value.get('ref'), 'source.ref')


def fingerprint(workspace, paths):
    if not isinstance(paths, list): raise ValueError('구현 근거는 상대경로 배열입니다.')
    result = {}
    for rel in paths:
        p = contained(workspace, rel)
        if not p.is_file(): raise ValueError('실제 파일 없음: ' + rel)
        result[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def validate_requirement(r):
    for k in ['id', 'requirement', 'criterion']: require_text(r.get(k), k)
    if type(r.get('required')) is not bool: raise ValueError('required true/false 필요')
    if r.get('status') not in ('confirmed', 'proposed', 'unresolved'): raise ValueError('정책 상태 오류')
    source_ok(r.get('source'))
    if r.get('implementation') not in ('not_started', 'in_progress', 'implemented'): raise ValueError('구현 상태 오류')
    if not isinstance(r.get('depends_on', []), list): raise ValueError('depends_on 배열 필요')


def update(state, patch, workspace):
    if not isinstance(patch, dict): raise ValueError('변경분 JSON은 객체입니다.')
    for field in ('requirements','checks','artifacts'):
        values = patch.get(field, [])
        if not isinstance(values, list) or any(not isinstance(x, dict) for x in values):
            raise ValueError(field + '는 객체 배열입니다.')
    if patch.get('expected_revision') != state['revision']: raise ValueError('기록 버전이 달라졌습니다. 다시 읽고 변경분을 합치세요.')
    if set(patch) - {'expected_revision','note','goal','requirements','checks','artifacts'}:
        raise ValueError('지원하지 않는 변경 키. 삭제·암묵적 전체 교체는 지원하지 않습니다.')
    require_text(patch.get('note'), '변경 이유')
    result = copy.deepcopy(state)
    if 'goal' in patch:
        goal = patch['goal']
        if not isinstance(goal, dict): raise ValueError('goal 객체 필요')
        require_text(goal.get('description'), '목표'); source_ok(goal.get('source'))
        result['goal'] = goal
    reqs = {r['id']: r for r in result['requirements']}
    seen = set()
    for delta in patch.get('requirements', []):
        rid = delta.get('id'); require_text(rid, '요구 ID')
        if rid in seen: raise ValueError('패치 내 요구 ID 중복')
        seen.add(rid)
        before = reqs.get(rid)
        r = {**(before or {'implementation':'not_started', 'depends_on':[]}), **delta}
        validate_requirement(r)
        validate_policy(r, before)
        if r.get("verification_mode", "standard") not in ("standard", "transition"):
            raise ValueError("verification_mode: standard/transition")
        # Any edited requirement invalidates its old verification, even if its status still says implemented.
        r['revision'] = before['revision'] + 1 if before else 1
        files = r.get('implementation_evidence', [])
        if r['implementation'] == 'implemented' and not files: raise ValueError(rid + ': 구현 파일 근거 필요')
        fingerprint(workspace, files)
        reqs[rid] = r
    for r in reqs.values():
        if any(x not in reqs or x == r['id'] for x in r.get('depends_on', [])): raise ValueError('의존 요구 없음/자기참조')
    def visit(rid, chain):
        if rid in chain: raise ValueError('의존 요구 순환')
        for dep in reqs[rid].get('depends_on', []): visit(dep, chain | {rid})
    for rid in reqs: visit(rid, set())
    checks = {x['id']: x for x in result['checks']}
    for check in patch.get('checks', []):
        cid = check.get('id'); require_text(cid, '검증 ID')
        if cid in checks: raise ValueError('검증 기록은 덮지 않습니다. 새 검증 ID를 사용하세요.')
        refs = check.get('requirements')
        if not isinstance(refs, list) or not refs or any(x not in reqs for x in refs): raise ValueError('검증의 요구 연결 오류')
        if check.get('requirement_revisions') != {rid:reqs[rid]['revision'] for rid in refs}: raise ValueError('검사한 요구 버전 불일치')
        if check.get('status') not in ('pass','fail','not_run'): raise ValueError('검증 상태 오류')
        validate_transition(check)
        if check['status'] == 'pass' and any(reqs[r].get('verification_mode') == 'transition' for r in refs) and not check.get('transition'):
            raise ValueError('상태 전환 요구에는 연속 관측 기록이 필요합니다.')
        if 'expected' not in check: raise ValueError('독립 기대값 필요')
        require_text(check.get('expected_source'), '기대값 출처')
        if check['status'] in ('pass', 'fail'):
            if 'actual' not in check: raise ValueError('실제값 필요')
            evidence = check.get('evidence_files', [])
            if not evidence: raise ValueError('실제 검증 기록 파일 필요')
            fingerprint(workspace, evidence)
        relevant = set(refs)
        def include_deps(rid):
            for dep in reqs[rid].get('depends_on', []):
                if dep not in relevant: relevant.add(dep); include_deps(dep)
        for rid in refs: include_deps(rid)
        check = copy.deepcopy(check)
        check['dependency_revisions'] = {rid:reqs[rid]['revision'] for rid in relevant}
        files = sorted({f for rid in relevant for f in reqs[rid].get('implementation_evidence', [])})
        check['fingerprints'] = fingerprint(workspace, files + check.get('evidence_files', []))
        check['recorded_at'] = stamp(); checks[cid] = check
    artifacts = {x['path']:x for x in result['artifacts']}
    for a in patch.get('artifacts', []):
        contained(workspace, a.get('path')); source_ok(a.get('source'))
        if type(a.get('required')) is not bool or a.get('format') not in ('json','csv','text','file'):
            raise ValueError('산출물 required/format 오류')
        artifacts[a['path']] = a
    result.update(requirements=list(reqs.values()), checks=list(checks.values()), artifacts=list(artifacts.values()))
    result['revision'] += 1
    result['history'].append({'revision':result['revision'],'at':stamp(),'patch':copy.deepcopy(patch)})
    return result


def artifact_issues(state, workspace):
    issues = []
    for a in state['artifacts']:
        if not a['required']: continue
        try:
            p = contained(workspace, a['path'])
            if not p.is_file() or not p.stat().st_size: raise ValueError('없거나 빈 파일')
            if a['format'] == 'json':
                value = read_object(p)
                if a.get('json_type') == 'array' and not isinstance(value, list): raise ValueError('JSON 배열 필요')
                if a.get('json_type') == 'object' and not isinstance(value, dict): raise ValueError('JSON 객체 필요')
            elif a['format'] == 'csv':
                with p.open(encoding='utf-8-sig', newline='') as f:
                    rows = list(csv.reader(f))
                    if not rows or not rows[0]: raise ValueError('CSV 헤더 없음')
        except (ValueError, OSError) as exc: issues.append(a['path'] + ': ' + str(exc))
    return issues


def assess(state, workspace):
    reqs = {r['id']:r for r in state['requirements']}
    groups = {'verified':[], 'implemented_unverified':[], 'unfinished':[], 'blocked':[]}
    findings = {}; required_issues = []
    for rid, r in reqs.items():
        fresh = []
        for check in state['checks']:
            if rid not in check['requirements']: continue
            versions = check.get('dependency_revisions', {})
            if any(reqs.get(k,{}).get('revision') != v for k,v in versions.items()): continue
            try:
                hashes = check.get('fingerprints', {})
                if fingerprint(workspace, list(hashes)) != hashes: continue
            except (ValueError, OSError): continue
            fresh.append(check)
        problem = [c for c in fresh if c['status'] == 'fail']
        not_run = any(c['status'] == 'not_run' for c in fresh)
        passed = any(c['status'] == 'pass' for c in fresh) and not problem and not not_run
        if r['status'] != 'confirmed' or problem or open_conflicts(r):
            group = 'blocked'
        elif r['implementation'] != 'implemented': group = 'unfinished'
        elif passed: group = 'verified'
        else: group = 'implemented_unverified'
        groups[group].append(rid)
        findings[rid] = {'category':group,'requirement':r['requirement'],'revision':r['revision'],
                         'current_checks':[c['id'] for c in fresh], 'required':r['required'],
                         'open_conflicts':open_conflicts(r),
                         'policy_note':'출처 분류 미기록' if not r.get('policy') else r['policy']['origin']}
    # A dependent feature is not complete while its declared prerequisites are unresolved/unverified.
    for _ in range(len(reqs)):
        changed = False
        for rid, r in reqs.items():
            group = findings[rid]['category']
            if group == 'blocked': continue
            dependencies = [findings[dep]['category'] for dep in r.get('depends_on', [])]
            if any(x in ('blocked', 'unfinished') for x in dependencies):
                groups[findings[rid]['category']].remove(rid)
                findings[rid]['category'] = 'blocked'; groups['blocked'].append(rid); changed = True
            elif group == 'verified' and 'implemented_unverified' in dependencies:
                groups[group].remove(rid)
                findings[rid]['category'] = 'implemented_unverified'
                groups['implemented_unverified'].append(rid); changed = True
        if not changed: break
    for rid,r in reqs.items():
        if r['required'] and findings[rid]['category'] != 'verified':
            required_issues.append(rid + ': ' + findings[rid]['category'])
    artifacts = artifact_issues(state, workspace)
    if not reqs: required_issues.append('요구사항 기록 없음')
    if not state.get('goal'): required_issues.append('목표 기록 없음')
    return {'goal':state.get('goal'),'revision':state['revision'],'groups':groups,'requirements':findings,
            'artifact_issues':artifacts,'delivery_issues':required_issues + artifacts,
            'limit':'기록·파일 지문 확인입니다. 원문 해석의 정확성이나 테스트가 실제 실행됐는지는 로그와 직접 대조해야 합니다.'}


def markdown(report):
    out = ['목표: ' + (report['goal']['description'] if report['goal'] else '미기록')]
    for key,label in [('verified','구현·검증 완료'),('implemented_unverified','구현됨·미검증'),('unfinished','아직 미완료'),('blocked','미정·실패·확인 필요')]:
        ids = report['groups'][key]
        out.append(f'- {label} {len(ids)}개: ' + (', '.join(ids) or '없음'))
    for rid,r in report['requirements'].items(): out.append(f"  {rid} | {r['requirement']} | {r['category']} | v{r['revision']}")
    out.extend('- 산출물 확인: ' + x for x in report['artifact_issues'])
    return '\n'.join(out)


def footer(report):
    """Stable, user-facing counts. Copy verbatim; let the agent choose only the next action."""
    out = ['목표: ' + (report['goal']['description'] if report['goal'] else '미기록')]
    for key,label in [('verified','완료·검증됨'),('implemented_unverified','구현됨·미검증'),
                      ('unfinished','미완료'),('blocked','확인 필요')]:
        ids = report['groups'][key]
        names = [report['requirements'][rid]['requirement'] for rid in ids[:3]]
        tail = ' 외 ' + str(len(ids)-3) + '개' if len(ids)>3 else ''
        out.append(f'{label}: {len(ids)}개 — ' + (', '.join(names)+tail if ids else '없음'))
    return '\n'.join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['init','update','status','preflight'])
    p.add_argument('--workspace', required=True); p.add_argument('--patch')
    p.add_argument('--format', choices=['json','markdown','footer'], default='json')
    a = p.parse_args()
    try:
        w = Path(a.workspace).resolve(); path = state_path(w)
        if not w.is_dir(): raise ValueError('기존 과제 폴더를 지정하세요.')
        if a.action == 'init':
            if path.exists(): raise ValueError('기존 상태 파일이 있습니다. 읽고 이어가세요.')
            atomic_write(path, initial())
        elif a.action == 'update':
            if not a.patch: raise ValueError('--patch 변경분 JSON 필요')
            # One writer per workspace. Revision lease rejects stale sequential updates.
            state = read_object(path); result = update(state, read_object(a.patch), w)
            if read_object(path)['revision'] != state['revision']: raise ValueError('갱신 충돌. 다시 읽으세요.')
            atomic_write(path, result)
        result = assess(read_object(path), w)
        print(footer(result) if a.format == 'footer' else markdown(result) if a.format == 'markdown' else json.dumps(result,ensure_ascii=False,indent=2))
        return 2 if a.action == 'preflight' and result['delivery_issues'] else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status':'기록 확인 필요','reason':str(exc)},ensure_ascii=False)); return 2


if __name__ == '__main__': raise SystemExit(main())
