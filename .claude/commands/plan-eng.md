---
description: "엔지니어링 계획 검토"
---

# /plan-eng — 엔지니어링 계획 검토

아키텍처, 테스트 커버리지, 성능, 보안을 기술적으로 검토한다.
`/plan-ceo` 이후 실행. `/plan-ceo` 판정이 NEEDS_REVISION이면 먼저 계획 수정 후 실행.

**AskUserQuestion 의무**: 기술 스택 선택, 아키텍처 패턴(모노리스 vs 마이크로), DB 선정, 배포 전략 등 해석이 2개 이상 가능한 결정은 반드시 AskUserQuestion으로 선택지 제시 후 확인. 추측 진행 금지.

---

## Phase 1: 컨텍스트 로드

```bash
node scripts/log-event.mjs command_start name=plan-eng
# 계획 파일 + CEO 검토 리포트 (있으면) 읽기
# 기존 코드베이스 구조 파악
# CLAUDE.md에서 빌드 명령, 기술 스택 확인
```

---

## Phase 2: 아키텍처 다이어그램

계획된 구조를 ASCII로 시각화:

```
[컴포넌트 A] ──→ [컴포넌트 B]
      │                │
      ↓                ↓
[데이터 레이어]    [외부 API]
```

**검토 포인트:**
- [ ] 단일 책임 원칙 — 컴포넌트가 너무 많은 일을 하는가?
- [ ] 순환 의존성 없는가?
- [ ] 기존 아키텍처와 일관적인가?
- [ ] 확장 포인트가 명확한가?

---

## Phase 3: 테스트 커버리지 맵

변경/추가될 각 코드 경로를 매핑:

```
[기능 X]
  ├── 정상 흐름 → ✓ 테스트 계획 있음
  ├── 에러 케이스 A → ✗ 테스트 없음 ← 추가 필요
  └── 엣지 케이스 B → ✗ 테스트 없음 ← 추가 필요
```

숫자 기반 커버리지 % 대신 **흐름 기반 맵**. 누락된 경로를 명확히.

---

## Phase 4: 성능 분석

잠재적 병목 식별:
- [ ] N+1 쿼리 가능성
- [ ] 동기 블로킹 I/O
- [ ] 메모리 누수 패턴
- [ ] 캐싱 전략 필요 여부
- [ ] 번들 크기 영향 (프론트엔드)

---

## Phase 5: 보안 검토 (빠른 스캔)

전체 `/cso` 대신 계획 범위에 한정:
- [ ] 새로운 입력 경로 — 검증 계획 있는가?
- [ ] 인증/권한 변경 — 권한 우회 가능성?
- [ ] 데이터 분류 — 민감 데이터 처리 방식?
- [ ] 의존성 추가 — 알려진 CVE 있는가?

보안 이슈 발견 시 → `/cso` 전체 감사 권장

---

## Phase 6: 구현 로드맵

coder 에이전트가 바로 착수할 수 있는 수준으로.

**Risky-first 정렬 (리뷰 강조용)**: 로드맵 상단에 "바뀔 가능성 높은 결정" 요약 블록(데이터 모델·타입 인터페이스·UX 플로우)을 먼저 제시 — 사용자가 실제로 바꿀 결정부터 검토하게 한다. 단 태스크 실행 순서(T1/T2 DAG)는 의존성 위상 정렬이 항상 우선 — blocked-by를 역전시키지 말 것 (출처: `reference/research/fable-field-guide-unknowns-2026-07.md`)

```markdown
### 구현 순서
T1: [태스크] — 파일: [목록] — 예상: [소요]
T2: [태스크] — 파일: [목록] — 예상: [소요] [blocked-by: T1]
T3: [태스크] — 파일: [목록] — 예상: [소요] [병렬: T2]

### 병렬 가능 태스크
- T2 ∥ T3 (파일 충돌 없음)

### 크리티컬 패스
T1 → T2 → T4 (총 예상 시간)
```

---

## Phase 7: 검토 리포트 저장

계획 파일 하단에 추가:
```markdown
## 엔지니어링 검토 리포트
날짜: [YYYY-MM-DD]

### 아키텍처 다이어그램
[ASCII]

### 테스트 커버리지 맵
[맵]

### 리스크
[목록]

### 구현 로드맵
[태스크 DAG]

### 판정: APPROVED | APPROVED_WITH_CONCERNS | NEEDS_REVISION
```

---

## 완료 출력
```json
{
  "status": "DONE | DONE_WITH_CONCERNS | BLOCKED",
  "verdict": "APPROVED | APPROVED_WITH_CONCERNS | NEEDS_REVISION",
  "implementation_ready": true,
  "parallel_tasks": ["T2", "T3"],
  "critical_path": ["T1", "T2", "T4"],
  "security_flag": false,
  "next": "orchestrator에게 구현 위임 가능"
}
```

## 원칙
- 다이어그램과 테스트 맵은 실제 파일 분석 기반 (추측 금지)
- `implementation_ready: true`면 orchestrator가 바로 PARALLEL_PLAN.md 작성 가능
- 보안 이슈 발견 시 `/cso` 권장 (강제 아님)
