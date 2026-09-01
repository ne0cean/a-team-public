---
description: "새 세션 시작 + 컨텍스트 로드"
---

---
description: 세션 시작 — 컨텍스트 로드 + 태스크 분류 + 즉시 실행
---

> **자동 트리거**: SessionStart 훅이 새 세션 시 자동 주입.
> 수동 `/vibe`는 컨텍스트 강제 리로드 시 사용.

## Step 0 — 상태 스캔 (vibe-init.sh)

```bash
node scripts/log-event.mjs command_start name=vibe
bash scripts/vibe-init.sh
```

**Step 0.03 — 배선 무결성 (수 초, 전체 프로젝트)**:
```bash
node ~/tools/A-Team/scripts/verify-wiring.mjs || echo "⚠️ 배선 깨짐 — 위 FAIL 항목 먼저 수리"
```
경계 드리프트(심링크·settings 경로·숨은 git 상태)는 세션 시작 시에만 잡을 수 있다. FAIL이면 작업 전에 수리.

**Step 0.5 — PMI 자동 감지** (전체 프로젝트, 2026-09-02 배선 — pmi.md가 약속만 하고 미배선이던 트리거):
```bash
git log --name-only --oneline HEAD~5..HEAD 2>/dev/null | grep -cE '^(lib/|\.claude/agents/|governance/|scripts/.*\.mjs)' || true
```
직전 5커밋이 lib/·agents/·governance/·scripts 중 **3개 이상 카테고리** touch, 또는 `governance/rules/*` 신규/수정 → 브리핑에 "메이저 통합 감지 — `/pmi` 실행 권장" 1줄 포함 (자동 실행 아님, 제안만).

**Step 0.69 — Gap Priority 1줄 요약** (a-team 레포에서만):
```bash
[ -f scripts/gap-priority.mjs ] && node scripts/gap-priority.mjs --summary 3 2>/dev/null || true
```
출력 예: `Gap #1: marketing.performance-marketing (score=16.0, cov=0%) | #2: sales-cs.lead-generation | Total: 28개`
이 줄을 브리핑 마지막에 포함한다. 없으면 스킵.

**Step 0.75 — Scheduled Reviews** (전체 프로젝트):
```bash
node /path/to/a-team/scripts/check-scheduled-reviews.mjs 2>/dev/null || true
```
- due 항목 있음 → 브리핑에 포함 + "예약 리뷰 N건 도래. 처리하시겠습니까?" 제안
- due 항목 없음 → 스킵
- 처리 후 해당 항목 status를 "done"으로 변경

**Step 0.7 — Daily Growth Brief** (a-team 레포에서만):
```bash
TODAY=$(date +%Y-%m-%d)
mkdir -p .context/briefs
# collect.json 없으면 자동 생성 (경량, Claude 불필요)
if [ ! -f ".context/briefs/${TODAY}-collect.json" ]; then
  node scripts/daily-brief-collect.mjs --save 2>/dev/null &&     echo "daily_brief: collect 자동 생성 완료" ||     echo "daily_brief: collect 실패 (scripts/daily-brief-collect.mjs 확인)"
fi
# growth.md 존재 여부 확인
if [ ! -f ".context/briefs/${TODAY}-growth.md" ]; then
  echo "daily_brief: growth 없음 — /daily-brief 실행 권장"
else
  echo "daily_brief: $(head -3 .context/briefs/${TODAY}-growth.md | grep -o '#.*' | head -1)"
fi
```
- collect.json 없음 → 자동 실행 (무조건, 사용자 확인 불필요)
- growth.md 없음 → Step 4 브리핑에 `/daily-brief` 제안 포함
- growth.md 있음 → Executive Summary 1줄 표시

**Step 0.8 — Design Token Check** (UI가 있는 프로젝트에서만):
```bash
# UI 파일 존재 확인
UI_EXISTS=$(find . -maxdepth 4 -name "*.jsx" -o -name "*.tsx" -o -name "*.vue" -o -name "*.svelte" 2>/dev/null | head -1)
if [ -n "$UI_EXISTS" ]; then
  DRIFT=$(node /path/to/a-team/scripts/design-drift-detect.mjs . --json 2>/dev/null | head -1)
  if [ -n "$DRIFT" ]; then
    TOKEN_FILE=$(echo "$DRIFT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tokenFile','NONE'))" 2>/dev/null)
    SCORE=$(echo "$DRIFT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('driftScore',0))" 2>/dev/null)
    RATING=$(echo "$DRIFT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('rating','?'))" 2>/dev/null)
    echo "design_tokens: ${TOKEN_FILE} (score: ${SCORE}/100, ${RATING})"
  fi
fi
```
- `NONE` → designer 에이전트 호출하여 토큰 생성 제안: "디자인 토큰이 없습니다. 생성할까요?"
- D/F 등급 → "디자인 드리프트 심각 (${SCORE}/100). 토큰 정비 권장"
- A/B 등급 → 1줄 표시 후 진행

**출력 해석**:
- `resume_active: true` → `/pickup` 으로 분기 (경량 복구)
- `actions` 있음 → 제안된 커맨드 안내
- `git_dirty > 0` → uncommitted 작업 존재
- `pending_p0 > 0` → P0 긴급 개선사항 안내

**분기 규칙**:
- `resume_active` 또는 `git_dirty > 5` 또는 `in_progress` 있음 → **pickup 경량 경로**
- 그 외 → **vibe 풀 경로** (Step 1~4)

**Step 0.85 — Domain Pattern Gate** (전체 프로젝트):
```bash
PATTERNS_DIR="/path/to/user/Projects/a-team/governance/patterns"
LOADED_PATTERNS=""

# Playwright/Browser 자동화 프로젝트 감지
if [ -d "scripts/browser" ] || find . -maxdepth 3 -name "playwright.config*" 2>/dev/null | grep -q .; then
  LOADED_PATTERNS="$LOADED_PATTERNS browser-automation"
  echo "pattern_gate: [browser-automation] scripts/browser 감지 → governance/patterns/browser-automation.md 로드됨"
fi

# Cloudflare Worker 프로젝트 감지
if [ -f "wrangler.toml" ] || [ -f "wrangler.json" ]; then
  LOADED_PATTERNS="$LOADED_PATTERNS api-error-handling data-mutation"
  echo "pattern_gate: [cloudflare-worker] wrangler.toml 감지 → api-error-handling.md + data-mutation.md 로드됨"
fi

# Visual QA 패턴 (browser 감지 시 함께)
if echo "$LOADED_PATTERNS" | grep -q "browser-automation"; then
  echo "pattern_gate: [visual-qa] → governance/patterns/visual-qa.md 로드됨"
fi

if [ -z "$LOADED_PATTERNS" ]; then
  echo "pattern_gate: 특정 도메인 미감지, 범용 모드"
fi
```
- **감지된 패턴 파일을 반드시 Read tool로 컨텍스트에 주입한다** (echo 메시지만으론 불충분, 절대경로 사용):
  - browser-automation 감지 → `Read /path/to/user/Projects/a-team/governance/patterns/browser-automation.md`
  - cloudflare-worker 감지 → `Read /path/to/user/Projects/a-team/governance/patterns/api-error-handling.md` + `Read /path/to/user/Projects/a-team/governance/patterns/data-mutation.md`
  - visual-qa 감지 → `Read /path/to/user/Projects/a-team/governance/patterns/visual-qa.md`
- 파일 Read 후 "설계 체크리스트" 섹션을 첫 번째 구현 액션 전에 반드시 확인
- 에러 발생 시: `Read governance/diagnostics/` 해당 플레이북으로 즉시 진단

**Step 0.9 — PRD Gate** (전체 프로젝트):
```bash
PRD_EXISTS=$(find . -maxdepth 3 -name "*prd*" -o -name "*PRD*" 2>/dev/null | grep -iE '\.md$' | head -1)
if [ -z "$PRD_EXISTS" ]; then
  echo "prd_gate: PRD 없음 — /prd 실행 필요"
else
  echo "prd_gate: $PRD_EXISTS"
fi
```
- PRD 없음 → 브리핑에 포함: "이 프로젝트에 PRD가 없습니다. `/prd`로 먼저 정의할까요?"
- PRD 있음 → 1줄 표시 후 진행
- hotfix/버그 수정 세션은 면제 (사용자가 명시)
- 상세: `governance/rules/prd-gate.md`

---

## Step 1 — 컨텍스트 로드

```bash
git pull --rebase --autostash origin $(git branch --show-current) 2>&1 | tail -3 || true

# A-Team 레포인 경우: pull 후 .claude/commands/ → ~/.claude/commands/ 자동 동기화
CURRENT_REPO=$(git rev-parse --show-toplevel 2>/dev/null || echo '')
if [ -d "$CURRENT_REPO/.claude/commands" ]; then
  GLOBAL_CMDS="$HOME/.claude/commands"
  REPO_CMDS="$CURRENT_REPO/.claude/commands"
  SYNCED=0
  while IFS= read -r -d '' f; do
    fname=$(basename "$f")
    global_file="$GLOBAL_CMDS/$fname"
    if [ ! -f "$global_file" ] || [ "$f" -nt "$global_file" ]; then
      cp "$f" "$global_file"
      SYNCED=$((SYNCED + 1))
    fi
  done < <(find "$REPO_CMDS" -maxdepth 1 -name "*.md" -print0)
  [ $SYNCED -gt 0 ] && echo "🔄 Commands sync: ${SYNCED}개 스킬 → ~/.claude/commands/ 복원"
fi
```

읽을 파일:
- `.context/ORIENT.md` — **실행 표면(모바일/web/desktop)·배포처·run 방법 3종 팩트.** 없으면 첫 실행성 액션 전에 확정하고 ≤6줄로 캡처. multi-surface(폰/Mac 등)면 어느 쪽이 진실인지 먼저 (2026-08-27 hsc split-brain 재발방지)
- `.context/CURRENT.md` — 현재 상태, Next Tasks
- `.context/{TEST_PLAN,REQUIREMENTS,FIRING_SPEC,PRD}.md` 등 SSOT — **실행성 태스크 착수 전 읽기.** 참조 근거는 SSOT지 추측이 아님
- `.context/DECISIONS.md` — 최근 결정사항 (있으면)
- `git log --oneline -5`

## Step 2 — 태스크 분류 (Opus / Sonnet)

CURRENT.md의 Next Tasks 분류:

**🔵 Opus**: 아키텍처 설계, 복잡한 리팩토링, 멀티파일 연쇄, 보안, 신규 핵심 기능
**🟢 Sonnet**: 구현, 버그 수정, 문서, 테스트, 단순 CRUD, 마이너 버그

## Step 3 — 실행 모드 결정

```
에이전트 1-2 + 독립      → 🟢 단일 터미널
에이전트 3-5 + 파일 분리  → 🟡 A-Team 오케스트레이션
설계 결정 / 옵션 비교     → 🟣 MoA 모드
```

**모델 추천** (CLAUDE.md 프로토콜):
1. Opus 필요 여부: (a) 새 설계 / (b) 옵션 비교 / (c) 5+ 파일 의존성
2. NO → 첫 줄에 전환 제안: "Sonnet으로 충분. 전환할까요?"

## Step 4 — 실행

브리핑: "마지막 [{커밋}]. 다음: [{태스크}]. [모드]. 시작."

**관련 명령어** (태스크 유형별):
- 구현 → `/tdd` → `/craft` → `/ship`
- 설계 → `/blueprint` → `/plan-eng`
- 리뷰 → `/review` → `/adversarial`
- 품질 → `/cso` → `/qa` → `/land`
- 야간 → `/zzz` → `/ralph`

---

## 상세 체크 항목 (vibe-init.sh 내부)

| 체크 | 설명 |
|------|------|
| A-Team sync | 6h 경과 시 자동 pull |
| Resume 감지 | RESUME.md 미완료 시 /pickup 제안 |
| launchd | 자동 재개 설정 여부 |
| Cold review | 30일 경과 시 /cold-review 제안 |
| Major integration | 최근 3커밋에 lib/agents/governance 변경 시 /optimize |
| Pending P0 | improvements/pending.md에 P0 있으면 알림 |
| Capability | capability-map.json 종합 점수 |
| Roadmap | team-roadmap.md 현재 Phase |

상세 로직: `scripts/vibe-init.sh` 참조
