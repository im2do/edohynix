# 실행 안내와 한계

[처음으로](../README.md) · [작업 흐름](WORKFLOW.md)

**명령은 AI가 현재 과제 폴더에서 실행하고 결과 파일을 읽습니다.** 직접 실행·설치·파일 쓰기가 제한되면 그 규칙을 따릅니다. 아래 입력명과 열 이름은 설명용 자리 이름입니다. 원문에서 실제 경로·열·필수 여부를 확인해 바꾸며, 예시 파일이 있다고 가정하지 않습니다.

## 경로를 먼저 고정

| 방식 | 스크립트 위치 | 상태 파일 |
|---|---|---|
| 설치함 | `FDE_HARNESS.json`의 package 아래 `scripts` (기본 `fde-harness/scripts`) | manifest의 progress |
| clone만 함 | `tools/edohynix/scripts` | 과제 폴더의 `FDE_PROGRESS.json` |

아래는 설치 방식입니다. 직접 읽기 방식은 접두 경로만 바꿉니다. 출력 폴더는 허용된 위치에 준비하고, 기존 결과는 지우지 말고 새 버전 이름을 씁니다. 경로에 공백이 있으면 따옴표로 감쌉니다.

## PDF: 추출과 판독을 분리

```bash
python3 fde-harness/scripts/pdf_read.py --doctor
python3 fde-harness/scripts/pdf_read.py "documents/guide.pdf" --pages 1-3,5 --output "worklog/pdf/guide-v1.json"
```

`--pages`를 빼면 전체 쪽수를 추출합니다. 예시 범위를 그대로 적용하지 말고 필요한 범위를 정합니다. 원본 SHA-256·총 쪽수·선택 쪽수·페이지별 텍스트/상태를 저장합니다. 출력 폴더는 자동 생성하며 기존 파일은 덮지 않습니다.

- `text_extracted`: 텍스트 추출 성공. 표의 열·단위·각주·이미지 판독 완료는 아닙니다.
- `needs_visual_check` / `extraction_failed`: 해당 쪽을 허용된 화면·렌더링으로 대조합니다. 빈 텍스트를 “규칙 없음”으로 바꾸지 않습니다.
- 종료 코드 2여도 일부 추출 결과가 저장됐을 수 있습니다. 콘솔 요약과 JSON의 해당 쪽을 확인합니다.
- 도구가 없으면 허용된 Python 환경을 먼저 확인합니다. 추가 설치가 허용될 때만 별도 환경에 필요한 엔진을 설치합니다. 자동 OCR·외부 전송은 없습니다.

## CSV·JSON: 행·ID·연결 확인

```bash
mkdir -p worklog/audit
python3 fde-harness/scripts/data_audit.py "data/source.csv" --id record_id --required amount unit --out "worklog/audit/source-v1.json"
python3 fde-harness/scripts/data_audit.py "results/output.csv" --id record_id --expected "data/source.csv" --out "worklog/audit/coverage-v1.json"
```

`record_id`, `amount`, `unit`은 실제 열 이름과 확인된 필수열로 바꿉니다. 결과 JSON은 명령 뒤 자동으로 화면에 모두 출력되지 않으므로 AI가 읽어야 합니다. **구조 점검·원본 ID 대조와 업무 판정은 다릅니다.** 상세 입력·필드·제한은 [데이터 스킬 실행 안내](../skills/fde-data/references/data-tools.md)를 읽습니다.

기본 크기 제한 20,000,000은 **바이트**이며 모델의 입력 토큰 제한이 아닙니다. CSV·TSV·JSON을 지원하며 XLSX·PDF를 자동 표로 변환하지 않습니다.

## 위치·토큰 매핑

```bash
python3 fde-harness/scripts/mapping_check.py "worklog/mapping.json" "worklog/tokens.json" --out "worklog/mapped-v1.json"
python3 fde-harness/scripts/mapping_check.py "worklog/mapping.json" "worklog/target-tokens.json" --reverse --out "worklog/reversed-v1.json"
```

매핑은 `[["원본 토큰", "대상 토큰"], ...]`, 입력은 순서를 보존한 문자열 배열입니다. 실제 값을 원문에서 추출해 만듭니다. 역방향 입력에는 **대상 쪽 토큰 배열**을 넣습니다. 표의 의미·방향·OCR 정확성, 한글 분해·재조합은 이 스크립트가 처리하지 않습니다. 자세한 실패 해석도 [데이터 스킬 실행 안내](../skills/fde-data/references/data-tools.md)에 있습니다.

## 누적 요구·완료 현황

```bash
python3 fde-harness/scripts/fde_state.py status --workspace . --format markdown
python3 fde-harness/scripts/fde_state.py update --workspace . --patch "worklog/change-001.json"
python3 fde-harness/scripts/fde_state.py status --workspace . --format footer
```

변경 JSON은 AI가 현재 revision을 읽고 작성합니다. 사용자에게 ID·스키마를 외우게 하지 않습니다. [기록 형식](../skills/fde-track/references/ledger-format.md)과 [정책 출처 형식](../skills/fde-track/references/policy-format.md)을 필요할 때만 읽습니다. 새 요구를 추가해도 이전 요구는 남고, 규칙·구현·검증 파일이 달라지면 이전 통과를 재확인합니다.

설치된 상태에서는 초기화하지 않습니다. 설치 없이 기록이 없고 쓰기가 허용될 때에만 `fde_state.py init --workspace .`를 사용합니다. 저장 실패는 미갱신으로 알립니다. 실행 로그·담당자 답변 원문 전체는 별도로 저장해야 합니다.

## 단계 전환·최종 설명 점검

```bash
python3 fde-harness/scripts/check_handoff.py --workspace . --stage build
python3 fde-harness/scripts/check_handoff.py --workspace . --stage deliver
python3 fde-harness/scripts/review_guards.py --workspace . --claims "worklog/claims.json"
python3 fde-harness/scripts/fde_state.py preflight --workspace .
```

- `build`: 출처·완료 조건이 있고 충돌 없는 확정 요구가 하나 이상인지 확인합니다. 모든 미정 요구가 확정돼야 시작하는 것은 아닙니다. 확인된 기능만 구현합니다.
- `deliver` / `preflight`: 등록한 필수 요구·검사·산출물 연결을 점검합니다. 과제 지침에서 제출할 것을 먼저 정확히 등록해야 의미가 있습니다.
- `claims`: [주장 기록 형식](../skills/fde-deliver/references/claim-format.md)의 파일·행·인용·지문을 대조합니다. 인용이 주장을 실제로 뒷받침하는지는 사람이 별도로 판단합니다.
- 연속 화면 동작은 실제 실행 후 [상태 전환 형식](../skills/fde-verify/references/transition-format.md)에 남깁니다. 양식을 채웠다는 이유로 실제 검증이 되는 것은 아닙니다.

등록되지 않은 요구를 자동 발견하거나 과제별 정답을 계산하는 도구가 아닙니다. 별도 제출 JSON을 요구하지 않는 과제에 내부 기록을 제출물로 추가하지 않습니다.

## 한국어 문장 점검

```bash
python3 fde-harness/scripts/korean_output_check.py "worklog/response.txt"
```

새로 작성한 설명문에서 불필요한 한자·일본어 문자를 찾습니다. 원문 인용·고유명사를 확인한 경우에만 정확한 문자열을 `--allow-text`로 제외합니다. 내용·원문은 자동 번역·치환하지 않으며 자동 응답 훅도 아닙니다.

## 종료 코드를 읽는 법

0은 **해당 명령의 점검 범위에서** 통과했다는 뜻입니다. 전체 기능의 정확성이나 전달 완료를 뜻하지 않습니다. 2는 확인 필요 또는 실행 오류일 수 있으므로 JSON의 status/reason/issues와 결과 파일 존재를 확인합니다. `fde_state update` 성공은 저장 성공이며 요구가 모두 완료됐다는 뜻이 아닙니다. 같은 명령을 무작정 반복하거나 결과 파일을 지워 통과시키지 않습니다.
