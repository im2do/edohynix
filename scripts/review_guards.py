#!/usr/bin/env python3
"""Validate policy provenance, transition observations and claim citations; never infer truth."""
import argparse
import hashlib
import json
from check_handoff import contained, read_object


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + ' 필요')


def citation(value, name):
    if not isinstance(value, dict): raise ValueError(name + ' 객체 필요')
    text(value.get('ref'), name + '.ref'); text(value.get('quote'), name + '.quote')


def validate_policy(req, before=None):
    policy = req.get('policy')
    old = (before or {}).get('policy')
    if policy is None:
        if old is not None: raise ValueError('기존 정책 출처는 삭제할 수 없습니다.')
        return
    if not isinstance(policy, dict): raise ValueError('policy 객체 필요')
    if policy.get('kind') not in ('business', 'design'): raise ValueError('policy.kind: business/design')
    if policy.get('origin') not in ('document', 'stakeholder', 'user_decision', 'assumption', 'design_decision'):
        raise ValueError('policy.origin 확인 필요')
    citation(policy.get('evidence'), '정책 출처')
    confirmed = policy.get('confirmation')
    if confirmed is not None:
        citation(confirmed, '확인 근거'); text(confirmed.get('authority'), '확인 주체')
    if req.get('status') == 'confirmed' and policy['kind'] == 'business':
        if policy['origin'] in ('assumption', 'design_decision') and confirmed is None:
            raise ValueError('가정·설계 선택은 업무 정책으로 확정할 수 없습니다. 권한 있는 확인 근거가 필요합니다.')
    conflicts = policy.get('conflicts', [])
    if not isinstance(conflicts, list): raise ValueError('conflicts 배열 필요')
    seen = {}
    for item in conflicts:
        if not isinstance(item, dict): raise ValueError('충돌 항목 객체 필요')
        cid = item.get('id'); text(cid, '충돌 ID')
        if cid in seen: raise ValueError('충돌 ID 중복')
        if item.get('status') not in ('open','resolved'): raise ValueError('충돌 상태 확인 필요')
        claims = item.get('claims')
        if not isinstance(claims, list) or len(claims) < 2: raise ValueError('충돌하는 두 출처를 보존하세요.')
        for claim in claims: citation(claim, '충돌 출처')
        if item['status'] == 'resolved':
            citation(item.get('resolution'), '충돌 해결 근거')
            text(item['resolution'].get('authority'), '충돌 해결 주체')
        seen[cid] = item
    for prior in (old or {}).get('conflicts', []):
        current = seen.get(prior['id'])
        if current is None or current['claims'] != prior['claims']:
            raise ValueError('기존 충돌과 양쪽 원문은 삭제·교체하지 않습니다. 해결 근거를 추가하세요.')


def open_conflicts(req):
    return [x['id'] for x in (req.get('policy') or {}).get('conflicts', []) if x['status'] == 'open']


def validate_transition(check):
    transition = check.get('transition')
    if transition is None: return
    if not isinstance(transition, dict): raise ValueError('transition 객체 필요')
    text(transition.get('before'), '변경 전 상태'); text(transition.get('action'), '실행한 조작')
    for name in ('state','derived','next_action','reopened'):
        obs = transition.get(name)
        if not isinstance(obs, dict): raise ValueError('전환 관측 누락: ' + name)
        if 'not_applicable' in obs:
            if name == 'state': raise ValueError('변경 후 상태는 생략할 수 없습니다.')
            text(obs['not_applicable'], name + ' 비해당 사유'); continue
        if 'expected' not in obs: raise ValueError(name + ': 기대값 필요')
        text(obs.get('source'), name + ': 기대값 출처')
        if check['status'] in ('pass','fail'):
            if 'actual' not in obs: raise ValueError(name + ': 실제값 필요')
            # Avoid Python equality treating true and 1 as interchangeable.
            same = json.dumps(obs['expected'],sort_keys=True) == json.dumps(obs['actual'],sort_keys=True)
            if check['status'] == 'pass' and not same:
                raise ValueError('전환 검증 불일치인데 통과로 기록됨: ' + name)


def review_claims(document, workspace):
    if not isinstance(document, dict) or not isinstance(document.get('claims'), list) or not document['claims']:
        raise ValueError('claims에 설명문별 검토 기록을 넣으세요.')
    rows, seen = [], set()
    for claim in document['claims']:
        if not isinstance(claim, dict): raise ValueError('claim 객체 필요')
        cid = claim.get('id'); text(cid,'주장 ID'); text(claim.get('text'),'검토 문장')
        if cid in seen: raise ValueError('주장 ID 중복')
        seen.add(cid)
        verdict = claim.get('verdict')
        if verdict not in ('supported','partial','contradicted','unverified'): raise ValueError('주장 판정 확인 필요')
        text(claim.get('reason'),'판정 이유')
        evidence = claim.get('evidence', [])
        if not isinstance(evidence,list): raise ValueError('evidence 배열 필요')
        issues, checked = [], []
        for e in evidence:
            try:
                if not isinstance(e,dict): raise ValueError('근거 객체 필요')
                p = contained(workspace,e.get('path'))
                body = p.read_bytes(); lines = body.decode('utf-8-sig').splitlines()
                start,end = e.get('start_line'),e.get('end_line')
                if type(start) is not int or type(end) is not int or not (1 <= start <= end <= len(lines)):
                    raise ValueError('실재하는 시작·끝 행 번호 필요')
                text(e.get('quote'),'원문 인용')
                if e['quote'] not in '\n'.join(lines[start-1:end]): raise ValueError('지정 행과 인용 불일치')
                digest = hashlib.sha256(body).hexdigest()
                if e.get('sha256') and e['sha256'] != digest: raise ValueError('이전 인용 이후 파일 변경')
                checked.append({**e,'sha256':digest})
            except (ValueError,OSError,UnicodeError) as exc: issues.append(str(exc))
        if verdict != 'unverified' and not checked: issues.append('판정을 뒷받침하는 확인 가능한 인용 없음')
        rows.append({'id':cid,'text':claim['text'],'verdict':verdict,'reason':claim['reason'],
                     'issues':issues,'evidence':checked})
    return {'claims':rows,'citation_ok':not any(x['issues'] for x in rows),
            'unresolved':[x['id'] for x in rows if x['verdict'] != 'supported' or x['issues']],
            'limit':'인용의 존재·위치·지문 검사입니다. 문장이 사실인지, 인용이 주장을 논리적으로 지지하는지는 원문과 코드·실행 결과를 별도로 대조하세요.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',required=True); p.add_argument('--claims',required=True)
    a=p.parse_args()
    try:
        result=review_claims(read_object(a.claims),a.workspace)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if not result['unresolved'] else 2
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(json.dumps({'status':'확인 필요','reason':str(exc)},ensure_ascii=False)); return 2

if __name__=='__main__': raise SystemExit(main())
