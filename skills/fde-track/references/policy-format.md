# 업무 규칙 출처 기록

요구사항 객체의 선택 필드 `policy`. 새 업무 규칙에는 반드시 기록한다. 기존 v1.1 기록은 읽을 수 있지만 출처 분류 미기록으로 표시한다. AI가 입력하며 사용자가 이 형식을 외울 필요는 없다.

```json
{
  "kind":"business",
  "origin":"assumption",
  "evidence":{"ref":"담당자 대화 3","quote":"아직 결정되지 않았습니다."},
  "conflicts":[{
    "id":"P1","status":"open",
    "claims":[
      {"ref":"담당자 대화 3","quote":"아직 결정되지 않았습니다."},
      {"ref":"개발 제안 4","quote":"한 가지 방법만 허용하는 안을 제안합니다."}
    ]
  }]
}
```

위 문구는 형식 설명용이며 실제 과제 정책이 아니다. kind는 business/design, origin은 document/stakeholder/user_decision/assumption/design_decision. evidence는 ref와 quote 필수다. 업무상 가정·설계 선택을 confirmed로 승격하려면 `confirmation:{"authority":"확인 권한이 있는 사람","ref":"답변 위치","quote":"확정 원문"}`이 필요하다. 문서·담당자 출처도 문구와 적용 범위를 직접 대조한다.

충돌을 해결하면 기존 두 claims를 유지하고 status=resolved와 `resolution:{authority,ref,quote}`를 붙인다. 열린 충돌은 완료를 막는다. 충돌 목록을 생략한 patch는 보존되지만, policy 전체를 교체할 때 기존 충돌을 빠뜨리면 갱신을 거부한다. 요구 revision이 바뀌므로 기존 통과 기록은 재사용되지 않는다. JSON을 손으로 우회 수정하지 말고 update를 사용한다.
