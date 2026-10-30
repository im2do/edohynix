# Codex FDE 키트 · edohynix

업무 요구를 데이터·규칙·기능·검증으로 연결하는 프로젝트용 스킬과 실행 도구입니다. 현재 프로젝트의 지침·권한·실행 제한을 우선하며, 필요한 단계의 스킬만 읽습니다.

## 1. 가져오기와 설치

Python 3.10 이상과 Git이 필요합니다. PDF 추출 엔진 외에는 기본 스크립트에 별도 Python 패키지가 필요하지 않습니다. 아래 명령은 실제 환경에서 허용된 실행 방식으로 사용합니다.

**프로젝트 작업 폴더에서** 실행합니다. 키트 원본 폴더 안에 설치하지 않습니다.

```bash
git clone --depth 1 https://github.com/im2do/edohynix.git tools/edohynix
# 파일을 쓰지 않고 설치 경로·충돌을 확인
python3 tools/edohynix/scripts/bootstrap_codex.py --workspace . --profile app
# 확인한 구성 적용
python3 tools/edohynix/scripts/bootstrap_codex.py --workspace . --profile app --apply
```

| 작업 | 프로필 | 스킬 |
|---|---|---|
| 웹앱·업무 화면 | `app` | 공통 10개 + UI 1개 |
| 데이터 분석 | `data` | 공통 10개 |
| 문서·보고서 | `document` | 공통 10개 |

기존 `README.md`는 수정하지 않습니다. `AGENTS.md`가 있으면 보존하고 `FDE_INSTRUCTIONS.md`를 별도로 만듭니다. 기존 파일 충돌이나 작업 폴더 밖 심볼릭 링크는 거부합니다. 설치 중 OS 쓰기 오류가 나면 일부 새 파일이 남을 수 있으므로 생성 목록을 확인하고 재설치를 반복하지 않습니다.

설치 후 요청:

> FDE_HARNESS.json의 guide와 package를 읽고 현재 프로젝트 지침 안에서 적용해줘. fde-route와 fde-track으로 기존 요구를 유지하며 필요한 다음 기능을 진행해줘. 실제 변경 작업마다 완료·미완료·미검증·확인 필요와 다음 행동을 보여줘.

### 설치 없이 사용

> tools/edohynix/skills/fde-route/SKILL.md와 tools/edohynix/skills/fde-track/SKILL.md를 읽고 필요한 스킬만 적용해줘. 스크립트는 tools/edohynix/scripts에서 실행해. 기존 작업 기록은 초기화하지 말고 읽어서 이어가줘.

상태 기록이 **없고 쓰기가 허용될 때만** 프로젝트 폴더에서 초기 생성합니다.

```bash
python3 tools/edohynix/scripts/fde_state.py init --workspace .
```

이 명령은 `FDE_PROGRESS.json`만 만듭니다. 스킬 설치나 전체 대화 백업은 하지 않습니다. 파일 쓰기·실행이 불가능하면 미저장·미실행 범위와 이어갈 메모를 남깁니다.

## 2. 필요한 스킬 선택

| 상황 | 스킬 | 확인할 출력 |
|---|---|---|
| 시작·재개·방향 변경 | `fde-route` | 지금 필요한 단계 |
| 목표·권한·예외 미정 | `fde-define` | 담당자에게 확인할 쟁점 |
| PDF 읽기 | `fde-pdf-read` | 쪽수·추출 실패·시각 확인 범위 |
| 표·결합·변환·매핑 | `fde-data` | 행·ID·단위·중복·원문 위치 |
| 규정·담당자 답 적용 | `fde-rules` | 조건·경계·예외·출처 |
| 확정된 기능 구현 | `fde-build` | 작은 기능 하나와 변경 근거 |
| 업무 화면 구성 | `fde-ui` (`app`) | 판단·다음 행동·오류가 보이는 화면 |
| 누적 요구 추적 | `fde-track` | 완료·미완료·미검증·확인 필요 |
| 결과 검증·오류 추적 | `fde-verify` | 독립 기대값·실제값·첫 불일치 |
| 기능별 전체 점검 | `fde-project-review` | 입력·예외·검증·출력·남은 확인 |
| 결과 전달 | `fde-deliver` | 산출물·실행 방법·검증·한계 |

스킬 이름으로 요청하거나 `skills/<이름>/SKILL.md`를 직접 읽게 합니다. 실제 작업 순서와 담당자 답변 전달 방법은 [작업 흐름](guides/WORKFLOW.md)에 있습니다.

## 3. 상태 기록과 재개

- `FDE_HARNESS.json`: 설치 경로, 운영 지침, 사용 스킬.
- `FDE_PROGRESS.json`: 목표·요구·검사·변경 이력의 기준 기록.
- `FDE_WORKSTATE.md`: 짧은 요약과 원문 위치 안내.
- `.agents/skills/`: 프로젝트에 복사된 스킬.
- `fde-harness/`: 스크립트·스킬·사용 안내.

설치 후 상태 조회:

```bash
python3 fde-harness/scripts/fde_state.py status --workspace . --format footer
```

새 대화에서는 현재 지침, 실제 상태 파일, 변경된 코드와 검증 기록을 먼저 읽습니다. 이전 요구를 지우거나 기록을 초기화하지 않습니다. 담당자 답변 원문·전체 대화·실행 로그는 별도로 저장해야 합니다.

Git 저장소를 갱신해도 이미 프로젝트에 복사된 스킬은 자동 갱신되지 않습니다. 기존 설치본을 덮어쓰지 말고 최신 키트의 필요한 `SKILL.md`를 직접 읽게 할 수 있습니다.

## 4. 기능별 프로젝트 리뷰

> $fde-project-review로 현재 솔루션을 읽기 전용으로 점검해줘. 실제 기능, 읽는 데이터, 중복·예외 처리, 구현 이유의 근거, 실제 검증, 출력과 영향, 미검증 사항을 한눈에 정리해줘.

출력은 **전체 흐름 → 기능별 점검표 → 결과에 영향을 주는 미확인 사항**입니다. 코드 확인·테스트 존재·실행 기록·화면 확인을 구분하고 미완료 기능도 남깁니다. 리뷰 요청만으로 코드·진행 기록을 바꾸거나 테스트·브라우저 자동 조작을 시작하지 않습니다.

[리뷰 스킬](skills/fde-project-review/SKILL.md) · [점검표 작성 기준](skills/fde-project-review/references/review-format.md)

## 5. 실행 도구

[도구별 명령·입력 형식·결과 해석](guides/TOOLS.md)에서 PDF 추출, CSV·JSON 점검, 매핑, 상태 추적, 근거 대조를 확인합니다. 스크립트는 구조·기록을 검사하며 업무 규칙 자체를 대신 결정하지 않습니다. 필요한 규칙은 확인된 원문으로 구현합니다.

특정 모델·외부 API 키·MCP 서버·자동 훅·전역 설정을 요구하지 않습니다. 플러그인 메타데이터는 지원 클라이언트에서만 사용하며 프로젝트 스킬 설치와 중복 등록하지 않습니다. 외부 라이브러리 설치와 자료 전송은 현재 환경의 권한을 따릅니다.

[MIT 라이선스](LICENSE)
