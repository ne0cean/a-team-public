---
description: 일간 성장 브리핑 — 외부 트렌드 크롤링 + 내부 진단 + 자동 적용
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch
---

# /daily-brief — Daily Growth Engine

> A-Team 자율 성장 엔진. 크롤링 → 분석 → **자동 적용** → 의장 보고.
> 보고만 하는 게 아니라 **실행**한다.

## 모드

| 모드 | 설명 | 사용 |
|------|------|------|
| **기본** (scan+apply) | 크롤링 + GREEN 자동 적용 + YELLOW 브랜치 + RED 기록 | `/daily-brief` |
| **report-only** | 크롤링 + 보고만 (적용 안 함) | `/daily-brief --report` |

사용자가 `--report` 또는 "보고만", "적용하지 마" 라고 하면 report-only.
그 외 기본값은 **scan+apply**.

## Step 1: 내부 데이터 수집

```bash
node scripts/log-event.mjs command_start name=daily-brief
mkdir -p .context/briefs
node scripts/daily-brief-collect.mjs --save
```

## Step 2: 중복 실행 방지

```bash
TODAY=$(date +%Y-%m-%d)
ls .context/briefs/${TODAY}-growth.md 2>/dev/null && echo "EXISTS" || echo "NEW"
```

- `EXISTS` → "오늘 이미 실행됨. 강제 재실행?" (확인 대기)
- `NEW` → Step 3 진행

## Step 3: Growth Engine 에이전트 호출

`.claude/agents/growth-engine.md` 에이전트를 호출한다.

프롬프트:
```
governance/rules/growth-engine.md를 읽고 규칙을 숙지하라.
.context/briefs/YYYY-MM-DD-collect.json을 읽고 내부 상태를 파악하라.

Phase 1: 크롤링 소스에서 최신 정보 수집 (Tier 1 필수, Tier 2/3은 요일 기준)
Phase 2: 각 발견의 A-Team 관련성 판단 + GREEN/YELLOW/RED 안전 등급 분류
Phase 3: GREEN은 즉시 적용+커밋, YELLOW는 브랜치 생성, RED는 기록만
Phase 4: .context/briefs/YYYY-MM-DD-growth.md 보고서 작성

모드: [scan+apply / report-only]
```

report-only 모드면 Phase 3를 건너뛰고 Phase 4에서 "적용 안 함, 제안만" 형태로 보고서 작성.

## Step 4: 결과 확인 + 의장 보고

에이전트 완료 후:

1. `.context/briefs/YYYY-MM-DD-growth.md` 읽기
2. 의장에게 핵심만 보고:

```
--- Growth Engine (YYYY-MM-DD) ---

적용 완료 (GREEN): N건
 - [파일]: [변경 내용]

검토 대기 (YELLOW): M건
 - branch: growth/YYYY-MM-DD-[topic]

관찰 (RED): K건
 - [트렌드 요약]

특이사항 없음 시: "오늘은 조용합니다. 기존 작업에 집중."
---
```

## Step 5: analytics 로깅

```bash
node scripts/log-event.mjs command_end name=daily-brief data='{"green_applied":N,"yellow_pending":M,"red_observed":K,"sources_crawled":S}'
```

## 자동 트리거

| 트리거 | 조건 | 모드 |
|--------|------|------|
| `/vibe` Step 0.7 | 오늘 growth.md 없음 | scan+apply |
| `/pickup` Step 2.7 | 오늘 첫 세션 | report-only (안전) |
| `/zzz` 자율 모드 | 수면 중 | scan+apply |
| 크론 | 매일 09:00 KST | scan+apply |

## 안전 장치

1. **GREEN 적용 후 vitest 필수** — 실패 시 자동 revert + YELLOW 격상
2. **1일 GREEN 상한 5건** — 초과분은 YELLOW
3. **인프라 모라토리엄 존중** — CURRENT.md 확인, 모라토리엄 중이면 GREEN도 문서만
4. **테스트 없이 완료 선언 금지** — 기존 A-Team 규칙 준수
5. **이사회 결의 참조** — `.context/briefs/` 이전 보고서 + CURRENT.md Next Tasks

## 오류 처리

| 상황 | 처리 |
|------|------|
| 웹 검색 전면 실패 | 내부 데이터만으로 보고서 + "외부 스캔 실패" |
| gh CLI 미설치 | WebSearch fallback |
| 에이전트 2회 실패 | collect.json 요약만 저장 |
| GREEN 적용 중 충돌 | revert + YELLOW 격상 |
| 브랜치 생성 실패 | growth-log.jsonl에 기록 + 보고 |

## 주기 연계

```
일간: /daily-brief  → 크롤링 + 자동 적용 + 보고
주간: /insights     → 내부 분석 리포트
월간: /board        → 전략 감사 + 이사회 결의
```

daily-brief가 매일 작은 개선을 적용하고,
insights가 주간 트렌드를 분석하고,
board가 월간 방향을 교정한다.

**A-Team은 의장이 쉬는 동안에도 성장한다.**
