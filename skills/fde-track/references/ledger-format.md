# 상태 기록 입력

목표·요구·검증·산출물을 한 progress JSON에 보관한다. WORKSTATE는 읽기 안내와 사람이 보는 요약이며 progress가 상세 상태의 기준이다. 원래 대화 전체를 저장하는 도구는 아니다. 출처 원문은 허용된 과제 폴더에 따로 보존한다.

기본 흐름: `init` → 현재 `status` → 변경분 JSON 작성 → `update` → `status`. 설치된 v1.1 이상은 progress 파일을 이미 만들므로 init을 반복하지 않는다. v1.0 프로젝트에서는 init이 새 FDE_PROGRESS.json을 만들 수 있지만 기존 산재한 기록을 자동 변환하거나 새 지침을 적용하지는 않는다. 원문과 대조해 필요한 요구를 옮겨야 한다.

첫 변경 예시 (모든 값은 가상 예시이며 현재 과제 규칙이 아님):

```json
{
  "expected_revision": 0,
  "note": "사용자가 목표와 첫 기능을 요청함",
  "goal": {"description": "자료를 조건별로 확인해 결과를 재열람", "source": {"kind":"user", "ref":"이번 대화의 최초 요청"}},
  "requirements": [{
    "id":"R1", "required":true, "status":"confirmed",
    "requirement":"입력 목록을 빠짐없이 읽기", "criterion":"입력의 고유 ID와 결과 ID가 일치",
    "source":{"kind":"user", "ref":"이번 요청"}, "implementation":"not_started"
  }]
}
```

다음 대화는 전체 배열 대신 `{"expected_revision":1,"note":"새 요구 추가","requirements":[새로운요구]}`만 넣는다. 앞의 R1은 유지된다. 기존 요구 변경도 같은 id로 **변경 필드만** 넣는다. 변경할 때마다 해당 요구 revision이 올라간다. 명시적 사용자의 범위 변경을 기록하려면 required=false 또는 status=proposed 등 실제 합의한 상태를 남기고 이유를 note에 적는다. 요구 삭제 기능은 없다.

구현 후 그 요구에 `implementation:"implemented"`, `implementation_evidence:["solution/processor.py"]`를 연결한다. 구현과 함께 새 검사 기록을 넣을 수도 있다. 검사 요구 revision은 갱신 후 값이어야 한다.

```json
{
  "id":"T1", "requirements":["R1"], "requirement_revisions":{"R1":2},
  "status":"pass", "expected_source":"입력 원본과 합의된 완료 조건",
  "expected":"원본 고유 ID 집합과 일치", "actual":"집합 일치, 누락 0",
  "evidence_files":["worklog/id_check.log"]
}
```

검사는 pass/fail/not_run. 0/false도 유효한 expected·actual 값이다. not_run을 pass로 고치지 말고 실제 실행 후 새 검사 ID로 남긴다. 실패를 고친 후에는 관련 요구 변경(구현 상태·변경 근거)을 기록하고 새 요구 버전에 대해 재검증한다. 같은 현 버전의 실패/미실행이 남으면 통과로 표시하지 않는다.

요구의 `depends_on:["R1"]`은 연결된 규칙이 바뀌면 이전 검증도 재확인하게 한다. 구현 파일 지문이 변하면 연결된 검증은 낡은 것으로 처리된다. 자동으로 관련 요구를 추론해 주지는 않으므로 연결을 빠뜨리지 않는다.

명시된 파일 산출물만 등록:

```json
{"path":"results/report.json", "required":true, "format":"json", "json_type":"array", "source":{"kind":"readme", "ref":"현재 과제 제출 항목"}}
```

format은 json/csv/text/file. `preflight`는 등록된 필수 파일의 존재·공란·JSON 형태 등을 확인한다. 앱 URL 제출만 요구하는 과제에 임의의 JSON을 추가하지 않는다. 파일 검사는 계산 정답·전체 웹 동작의 증명이 아니다.
