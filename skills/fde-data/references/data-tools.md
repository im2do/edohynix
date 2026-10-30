# 구조·ID·매핑 점검의 실제 사용

설치됐으면 manifest.package 아래 scripts, clone만 했다면 키트 scripts를 사용한다. 아래 명령의 파일·열 이름은 설명용이며 실제 과제에서 확인해 바꾼다. 표를 만들거나 필수열을 임의로 발명하지 않는다.

## 구조 검사

```bash
mkdir -p worklog/audit
python3 fde-harness/scripts/data_audit.py data/source.csv --id record_id --required amount unit --out worklog/audit/source-v1.json
```

입력: CSV/TSV 또는 객체 배열 JSON. ID 열을 명시한다. UTF-8 BOM은 기본 지원하며 확인된 다른 인코딩만 `--encoding cp949` 등으로 지정한다. JSON 최상위 객체를 자동으로 배열로 추정하지 않는다.

읽을 출력:
- records_total/records_checked: 읽은 레코드 수. 문제 있는 행을 제거했다는 뜻이 아니다.
- unique_ids/duplicate_ids: ID와 중복 위치. 합법적인 일대다이면 규칙에 따라 별도 검증한다.
- issues/field_issues: 행 폭, 필수 필드 없음·null·공백. 0과 false는 공백으로 보지 않는다.
- id_locations: CSV 레코드·물리적 줄 범위 또는 JSON 배열 위치.
- sha256: 검사한 파일의 지문. 다른 버전 파일과 혼동하지 않는다.

중복 헤더·JSON 중복 키·잘못된 JSON 숫자는 실행 불가로 알린다. 마지막 값으로 조용히 덮지 않는다. CSV 값은 문자열로 보존하므로 이 검사가 수치·날짜·업무상 유효성까지 보장하지 않는다. 누락 필수열은 비어 있는 데이터셋에서 행별 검사만으로 입증할 수 없으므로 헤더와 0건 자체의 적합성도 확인한다.

## 원본 대비 누락·증식

```bash
python3 fde-harness/scripts/data_audit.py results/output.csv --id record_id --expected data/source.csv --out worklog/audit/coverage-v1.json
```

결과와 원본의 **ID별 출현 횟수**를 대조한다. coverage.differences의 expected/actual을 읽는다. JSON 숫자 1과 문자열 "1"도 서로 다르다. 정당한 필터·일대다 결과도 차이로 나타날 수 있으므로 대상 범위와 제외 사유를 대조한다. 무조건 0차이를 만들려고 원본 행을 제거하지 않는다. 같은 ID 안의 금액·기간·합계는 별도 검증한다.

`--max-bytes` 기본 20,000,000은 파일 바이트 제한이다. 제한 초과 시 자르지 않고 중단한다. 범위를 나눌 때 전체 건수·ID·읽지 못한 범위를 기록한다. 모델 입력 토큰 제한과 구분한다.

## 일대일 토큰 변환

```bash
python3 fde-harness/scripts/mapping_check.py worklog/mapping.json worklog/tokens.json --out worklog/mapped-v1.json
```

입력 표는 문자열 쌍 배열, 토큰은 순서 있는 문자열 배열이다. 매핑 표의 각 원본·대상은 유일해야 한다. target 토큰으로 원본을 찾을 때는 `--reverse`를 쓴다. 입력·출력 수, trace의 위치별 input/output, roundtrip을 확인한다. 매핑 없는 토큰은 null과 ‘매핑 없음’으로 남기고 삭제하지 않는다.

왕복 통과는 **제공한 표 안에서** 맞는다는 뜻이다. 원문을 잘못 옮긴 표도 왕복은 통과할 수 있으므로 대표 위치·방향·중복을 시각 자료와 대조한다. 한글 입력은 음절 분해 → 실제 키 단위 분해(겹모음·받침·Shift 포함 여부) → 위치 매핑 → 재조합을 따로 구현·검증한다. 단순 Unicode 분해가 키보드 입력 순서와 같다고 가정하지 않는다.

## 출력 보존

`--out`은 기존 파일을 덮지 않으며 부모 폴더가 필요하다. 결과는 파일에 기록되므로 AI가 실제로 열어 읽는다. 종료 2이면 생성된 결과의 확인 필요인지 실행 불가인지 구분한다. 두 도구 모두 원문 OCR·정책 해석·계산 정답·문장 조합을 대신하지 않는다.
