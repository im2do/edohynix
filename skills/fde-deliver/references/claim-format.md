# 설명문과 실제 근거 대조

`{"claims":[...]}`에 실제 제출 문장별 id, text, verdict, reason, evidence를 적는다. verdict는 supported/partial/contradicted/unverified. evidence는 `{path,start_line,end_line,quote}`이며 경로는 작업 폴더 안 상대경로다. 이전 검사에서 받은 sha256을 함께 넣으면 원문 변경도 확인한다.

```json
{"claims":[{
  "id":"C1","text":"검사 대상의 원본 식별자를 보존했습니다.",
  "verdict":"supported","reason":"원본과 출력의 ID 목록 비교 로그를 확인했습니다.",
  "evidence":[{"path":"worklog/id-check.log","start_line":1,"end_line":1,"quote":"missing=0, extra=0"}]
}]}
```

위 로그는 실제로 존재할 때만 사용한다. 행 번호는 1부터 시작한다. 다중행 CSV의 논리 레코드와 실제 파일 행을 혼동하지 않는다. PDF는 쪽수 추출 결과를 별도 텍스트에 보존한 뒤 해당 텍스트의 행·원본 쪽수를 함께 설명한다. 이미지·브라우저 동작은 확인 방법과 실제 관측을 로그로 남긴다.

파일과 인용이 존재해도 그 주장이 옳다는 뜻은 아니다. 자료의 기준 시각·연결 키·버전을 확인하고 반대 근거도 검토한다. “없다/미구현이다”는 검색 범위와 조회한 파일·실행 증거가 있어야 한다. 부분 검증을 전체 완료로 표현하지 않는다.
