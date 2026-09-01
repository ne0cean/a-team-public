---
description: 디자인 서브시스템 진입점 — 브리핑·생성·감사·썸네일을 단일 진입점으로 라우팅
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

> Analytics: `node scripts/log-event.mjs command_start name=design` — 실행 시작 시 반드시 호출

# /design — 디자인 서브시스템 라우터

인수 없이 호출하면 대화형 메뉴를 제공한다.
인수가 있으면 해당 서브커맨드로 바로 분기한다.

## 서브커맨드

| 인수 | 실행 | 설명 |
|------|------|------|
| `brief` | `/design-brief` | 디자인 브리핑 생성 — tone/variant/density 결정 |
| `generate` | `/design-generate` | 비주얼 에셋 생성 (이미지·SVG·컴포넌트) |
| `audit` | `/design-audit` | AI 냄새 22개 룰 + a11y 검사 |
| `thumbnail` | `/design-thumbnail` | 썸네일 원스탑 생성 |

## 실행 흐름

### 인수 있는 경우
```
/design brief   → /design-brief 실행
/design audit   → /design-audit 실행
/design generate → /design-generate 실행
/design thumbnail → /design-thumbnail 실행
```

### 인수 없는 경우 (대화형 메뉴)

다음 중 필요한 것을 선택하세요:

```
1. /design-brief    — 디자인 방향 먼저 잡기 (새 UI 작업 시작 전)
2. /design-generate — 비주얼 에셋 바로 생성
3. /design-audit    — 기존 UI/이미지 AI 냄새 검사
4. /design-thumbnail — 썸네일 제작
```

## 권장 순서

새 UI 작업:
1. `/design brief` → 방향 결정
2. `/design generate` → 에셋 생성
3. `/design audit` → AI smell 검사

기존 UI 검토:
1. `/design audit` → 현황 파악
2. `/design brief` → 개선 방향 재설정

## 참고 문서
- 디자인 철학: `governance/skills/design/README.md`
- 에이전트: `governance/skills/design/agents/`
- 프롬프트 스택: `governance/skills/design/stacks/`
