---
description: /blueprint — 에이전트/자동화 시스템 설계 문서(.md) 생성. 구조화 인터뷰 → 작업 컨텍스트 + 워크플로우 + 구현 스펙이 담긴 blueprint-<task-name>.md 저장 후 validator로 구조 검증. `/office-hours` 다음, `/plan-eng`/`/autoplan` 이전에 호출
---

# Blueprint

> 출처: [byungjunjang/jangpm-meta-skills](https://github.com/byungjunjang/jangpm-meta-skills) (MIT) — A-Team 규격으로 포팅

## Overview

구조화된 인터뷰로 사용자의 자동화 과제를 이해한 뒤, 완전한 에이전틱 시스템 설계 문서를 생성한다. 산출물은 Claude Code 구현 참조로 바로 사용 가능한 단일 `.md` 파일.

**AskUserQuestion 의무**: 아키텍처 선택(단일 에이전트 vs 멀티), 도구 선정, 데이터 흐름 방향 등 해석이 2개 이상 가능한 결정은 반드시 AskUserQuestion으로 선택지 2-4개 제시 후 확인. 추측 진행 금지.

**`_TBD_` 마커 전략**: 불명확한 부분은 발명하지 않고 `_TBD_`로 명시. AI가 추측으로 채우는 것보다 빈 칸이 낫다.

## Before Starting

**다른 것을 하기 전에 참조 파일 둘을 먼저 읽어라.** Phase 2에서 적용할 문서 구조와 설계 규칙을 담고 있다. 건너뛰면 출력이 불완전해진다.

1. `governance/skills/blueprint/document-template.md` — 출력 파일의 섹션별 전체 템플릿
2. `governance/skills/blueprint/design-principles.md` — 에이전트 구조, 검증, 데이터 전달, 커맨드 vs 서브에이전트 설계 규칙
3. *(선택)* `governance/skills/blueprint/example-blueprint.md` — 주석 포함 샘플 블루프린트 문서로 calibration

## Workflow

### Phase 1: Assess & Interview

사용자 입력을 아래 4개 영역에 대해 평가. **빈 부분만 묻는다.** 모든 영역이 충분히 명확하면 바로 Phase 2로.

| 영역 | 평가 대상 | 예시 질문 |
|------|---------|-----------|
| **Goal & success criteria** | 궁극 목표가 명확한가? 성공/실패를 판정할 수 있는가? | "어떤 결과가 나와야 이 에이전트가 성공했다고 볼 수 있나요?" |
| **Task procedure** | input→output 스텝이 정의됐는가? 분기 조건을 아는가? | "A 이후 B로 갈지 C로 갈지는 어떤 기준으로 판단하나요?" |
| **Agent organization** | 단일 vs 멀티 에이전트 선호? 명확한 역할 분리가 있는가? | "하나의 에이전트가 순차 처리하면 되나요, 아니면 분리할 역할이 있나요?" |
| **Tools & tech** | 사용 중인 기존 도구/API가 있는가? 없으면 옵션 제안. | "지금 쓰는 도구가 있나요? 없다면 이런 방식들이 가능한데 어떤 게 맞을까요?" |

**인터뷰 규칙:**
- **Blindspot pass 선행 제안**: 사용자가 낯선 도메인/코드베이스라고 밝히거나 답변에서 감지되고 **4영역에 빈 부분이 남아 있으면**, 인터뷰 전에 blindspot pass 1회 제안 (브리프가 이미 완전하면 기존 규칙대로 바로 Phase 2) — unknown unknowns를 먼저 찾아 설명하고, 그걸 바탕으로 인터뷰 질문을 재구성 (출처: `reference/research/fable-field-guide-unknowns-2026-07.md`)
- 질문은 구체적이고 probing 해야 함. 일반적/정형적 질문 금지
- 사용자가 "모르겠다" / "알아서 해줘" 하면: 합리적 기본값 적용, 선택과 근거를 말한 뒤 피할 수 없는 결정만 묻기
- 관련 질문 그룹핑 — 한 턴에 3개 초과 질문 금지

### Phase 2: Generate Design Document

요구사항이 명확해지면 작성 전에 인터뷰 결과를 문서 섹션으로 매핑:

| 인터뷰 발견 | → 문서 섹션 |
|---|---|
| 왜 필요한가, 어떤 문제를 푸는가 | § 1. 작업 컨텍스트 › 배경 및 목적 |
| 범위 포함 / 제외 | § 1. 작업 컨텍스트 › 범위 |
| 입력 형식, 출력 형식, 트리거 | § 1. 작업 컨텍스트 › 입출력 정의 |
| 기술 제약, API 한도 | § 1. 작업 컨텍스트 › 제약조건 |
| Step-by-step 프로세스, 분기 로직 | § 2. 워크플로우 정의 |
| 에이전트가 결정 vs 코드가 처리 | § 2. LLM 판단 vs 코드 처리 구분 |
| 사용 도구/API | § 3. 스킬/스크립트 목록 |
| 단일 vs 멀티 에이전트 선호 | § 3. 에이전트 구조 |
| 실패 조건, 재시도 기대 | § 2. 단계별 상세 › 실패 시 처리 |

`governance/skills/blueprint/document-template.md` 템플릿으로 모든 섹션 채움. `governance/skills/blueprint/design-principles.md` 설계 규칙 적용.

현재 작업 디렉토리에 `blueprint-<task-name>.md`로 저장.

**출력 규칙:**
- **Risky-first 정렬**: 템플릿 섹션 골격(§1→§2→§3 — validator가 헤더 순서를 검사)은 유지한 채, **각 섹션 안에서** 바뀔 가능성 높은 결정(데이터 모델·타입 인터페이스·UX 플로우)을 앞에 배치. 필요 시 문서 최상단에 "리스크 결정 요약" 블록 추가(검사 대상 헤더 이동 금지) — 리뷰어가 실제로 바꿀 것부터 보게 한다
- CLAUDE.md, AGENT.md, 커맨드 파일 내용은 **작성 안 함** — 이름과 역할만
- 구현 스펙은 구조와 책임만. 코드나 프롬프트 아님
- 모든 워크플로우 스텝에 성공 기준 + 검증 방법 + 실패 처리
- **하위 모델 실행 가능 게이트**: 블루프린트는 Sonnet급이 추가 질문 없이 단독 실행할 수 있을 만큼 결정(데이터 모델·인터페이스·리스크)이 명시돼야 한다 — 계획은 싼 모델이 실행할 자산
- **모든 블루프린트 문서에 "A-Team 표준 커맨드 규칙" 섹션 항상 포함**. 설계에 정의된 커맨드는 구현 시 `.claude/commands/<name>.md` 형식을 따른다 (자세한 규격은 `design-principles.md` › A-Team 커맨드 생성 표준). 문서에 **`A-Team 표준 커맨드` 또는 `.claude/commands/` 문자열**이 리터럴로 포함되어야 한다 — 구조 validator가 체크함.

**저장 전 완성도 체크** — 각 항목 채워졌는지 확인:
- [ ] 모든 워크플로우 스텝에 성공 기준 + 검증 방법 + 실패 처리
- [ ] LLM vs 스크립트 책임 테이블 채워짐
- [ ] 폴더 구조 정의됨
- [ ] "A-Team 표준 커맨드 규칙" 섹션 존재 + `.claude/commands/` 또는 `A-Team 표준 커맨드` 문자열 포함
- [ ] "TBD" 또는 빈 셀 없음

### Phase 2.5: Validate Document

저장 후 사용자에게 문서를 제시하기 전에 구조 validator를 실행.

A-Team 레포 로컬 경로에서 실행:

```bash
node scripts/log-event.mjs command_start name=blueprint
python scripts/validate-blueprint.py ./blueprint-<task-name>.md
```

A-Team 외부 프로젝트에서 실행 중이면 A-Team 절대 경로:

```bash
python /path/to/a-team/scripts/validate-blueprint.py ./blueprint-<task-name>.md
```

검증 실패 시 문서 수정 후 재실행. 이 스크립트는 구조만 체크 (필수 섹션, 스텝 필드, 구현/워크플로우 섹션 존재) — 내용 품질은 체크 안 함.

스크립트를 찾을 수 없으면 (첫 설치 또는 파일 누락) 스크립트 검증 스킵 후 수동으로 Phase 2 완성도 체크리스트 확인.

### Phase 3: Review

문서 제시 후 인터뷰 중 내린 핵심 설계 결정을 요약:

- 에이전트 구조 선택 (단일 vs 멀티) 및 이유
- 확정된 트레이드오프 (예: "rule-based 감지가 fragile 해서 LLM이 step X 판단")
- 설계를 형성한 제약

그 다음 질문: "이 결정들이 의도와 맞나요? 바꾸고 싶은 게 있으면 알려주세요."

요청된 변경을 적용하고 재확인.

### Phase 3.5: 설계 결정 DB 기록

블루프린트 확정 후 핵심 설계 결정을 `.context/design-decisions.md`에 append:

```markdown
## [날짜] [프로젝트명]
- **결정**: [무엇을 선택했는가]
- **대안**: [검토했지만 선택하지 않은 것]
- **근거**: [왜 이 결정을 내렸는가]
- **참조**: [블루프린트 파일 경로]
```

파일이 없으면 생성. 기존 내용 하단에 append (덮어쓰기 금지).
이 기록은 향후 유사 프로젝트에서 과거 결정을 참조하는 데 사용된다.

---

## A-Team 통합 흐름

```
/office-hours (아이디어 발견/검증)
    ↓
/blueprint (설계서 .md 생성)
    ↓
/autoplan 또는 /plan-eng (구현 계획 검토)
    ↓
/ralph 또는 /craft (구현)
    ↓
/autoresearch (커맨드 품질 최적화 — 선택)
```

## References

- **`governance/skills/blueprint/document-template.md`**: 출력 설계 문서의 전체 템플릿 (모든 섹션, 형식, 테이블)
- **`governance/skills/blueprint/design-principles.md`**: 폴더 구조, 에이전트 아키텍처, 검증 패턴, 실패 처리, 데이터 전달, 커맨드 vs 서브에이전트의 설계 규칙
- **`scripts/validate-blueprint.py`**: 블루프린트 문서 구조 validator

$ARGUMENTS
