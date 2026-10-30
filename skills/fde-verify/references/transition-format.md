# 상태 전환 검증 기록

상태 변경 요구에 `verification_mode:"transition"`을 설정한다. 기존 checks의 기대값·실제값·로그 외에 transition을 추가한다. 관측 값은 테스트에서 실제 얻은 값이며 예시를 복사해 통과시키지 않는다.

```json
{
  "before":"변경 전 상태",
  "action":"실제로 수행한 조작",
  "state":{"expected":"기대 상태","actual":"관측 상태","source":"요구 원문 위치"},
  "derived":{"expected":[],"actual":[],"source":"파생 후보 규칙 위치"},
  "next_action":{"expected":"기대 안내","actual":"실제 안내","source":"다음 행동 요구 위치"},
  "reopened":{"not_applicable":"과제에 저장·재열람 기능이 요구되지 않는 읽기 전용 보기"}
}
```

도구는 pass에 기록한 기대·실제 값이 다른 경우 거부한다. 자연어가 같은 뜻이더라도 문자열이 다르면 같다고 추정하지 않는다. 의미를 비교할 경우 실제 관측을 보존한 로그와 별도로 구조화한 결과를 넣는다. not_applicable에는 이유가 필요하고 state는 생략할 수 없다. 단순 계산 작업에는 이 형식을 강제하지 않는다. 실제로 실행하지 않은 단계는 not_run으로 기록한다.
