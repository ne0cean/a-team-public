---
description: "세션 종료 — 커밋 + 상태 갱신"
---

---
description: 세션 종료 — 상태 갱신, 빌드 검증, 커밋, push (+ 선택: Research Mode)
---

다음 순서대로 세션을 마무리합니다.

## Step 0 — Pre-flight: 미완료 AC 확인

세션 종료 전 미완료 AC가 없는지 확인한다.

```bash
cat ~/.claude/current-task-ac.txt 2>/dev/null | grep "\- \[ \]" || echo "✅ 미완료 AC 없음"
```

- **미완료 AC 있음** → VERIFY CMD 실행 후 완료 선언, 또는 session-checkpoint.txt에 저장 후 다음 세션으로 이관
- **없음 또는 파일 없음** → Step 0.5 진행


## Step 0.5 — RESUME.md 계약 대조 (stale 방지)

RESUME.md가 `status: in_progress`인데 세션 목표가 실제로는 끝났으면 반드시 닫는다.

```bash
grep -l "status: in_progress" RESUME.md 2>/dev/null && head -12 RESUME.md
```

- **in_progress + 목표 완료됨** → `status: done` + In Progress 체크박스 `[x]` 갱신 (커밋 해시 병기)
- **in_progress + 진짜 미완료** → 그대로 두고 In Progress 목록만 최신화
- **파일 없음/이미 done** → Step 1 진행

> 근거: 2026-07-06 stale RESUME이 다음 세션 vibe를 pickup으로 오분기 — 완료된 P1 3건을 재구현할 뻔 (Pre-flight Gate 참조)


## Step 1 — CURRENT.md 갱신
`.context/CURRENT.md`를 갱신한다 (없으면 스킵):
- `In Progress Files` → `(없음)` 으로 비우기
- `Last Completions` → 방금 완료한 작업 추가 (날짜 포함)
- `Next Tasks` → 다음 할 일 업데이트. **`[x]` 완료 항목은 삭제** (SESSIONS.md에 기록됨)
- `Blockers` → 현재 막힌 점 기록
- **위생 체크** (`governance/rules/document-hygiene.md`):
  - 200줄 초과 시 Last Completions 2주 이전 항목 → SESSIONS.md 이관
  - 완료된 Phase 체크리스트 → 1줄 요약으로 축약

```bash
node scripts/rollup-current.mjs        # 7일 경과+완료 섹션 자동 SESSIONS 이관 (게이트 200줄 자동 유지)
```

## Step 1.5 — Idea Harvest (조건부, memory/idea-registry.md 존재 시만)

```bash
ls memory/idea-registry.md 2>/dev/null
```

**파일 없으면 → 즉시 스킵.**

**파일 있으면 → 아이데이션 세션 판별:**
- 이 세션에서 `/brainstorm`, `/office-hours`, `/idea`, `/prd` 등 아이데이션 커맨드를 사용했거나
- 대화에 새 기능/메커닉 제안, 전략 전환, 프레이밍 발견 등 아이디어 패턴이 있는 경우만 진행
- **코딩/버그 수정/리팩토링만 한 세션 → 스킵** (레지스트리 읽지 않음)

**진행 시:**

1. `memory/idea-registry.md`를 읽고, 세션 대화에서 감지된 아이디어 각각을 ID/이름 매칭:
   - **매칭 있음** → 상태/리뷰메모 업데이트 제안
   - **매칭 없음** → 레지스트리 카테고리 헤더(`## X. 카테고리명`) 파싱하여 자동 분류 + 해당 카테고리 마지막 ID+1 부여 + status=개념, Ph=-
   - **이미 이 세션에서 `/brainstorm` Step 4.5 또는 `/idea`로 반영된 건 제외**

2. 변경 사항을 테이블로 제시:
   ```
   | 액션 | ID | 이름 | 변경 내용 |
   |------|----|------|----------|
   | 신규 | B18 | ... | status=개념, Ph=1 |
   | 업데이트 | E06 | ... | status: 개념→설계됨 |
   ```

3. 사용자 승인 → idea-registry.md 수정. 스킵 → 그대로 진행 (강제 아님).

## Step 2 — SESSIONS.md 로그 추가
`.context/SESSIONS.md`에 오늘 세션 항목 추가 (없으면 스킵):
```
## [YYYY-MM-DD] 세션 제목

**완료**: ...
**이슈**: ...
**빌드**: ✅/❌
```

## Step 2.5 — 종료 상태 블록 (quick-recap 컨벤션, BuilderIO 흡수)

세션 마지막 사용자 보고는 **컬러 상태블록**으로 시작한다 — 한눈에 상태 파악:

```
🟢 <한 일 요약> | NOW: <이번에 한 것> | NEXT: <다음>
🟡 <부분 완료/주의> 있으면 한 줄
🔴 <차단/실패> 있으면 한 줄 + 사유
```

- 🟢 = 완료·검증됨, 🟡 = 부분/미검증/주의, 🔴 = 차단·실패. 해당 없는 색은 생략.
- 진실 계약 준수: 🟢은 **tool output으로 확인된 것만**. 미검증은 🟡.
- 블록 다음에 상세(커밋 해시, 변경 파일 등) 이어붙임.

## Step 3 — 빌드 검증
프로젝트 타입을 자동 감지하여 실행:
```bash
[ -f package.json ]   && npm run build
[ -f Cargo.toml ]     && cargo test
[ -f pyproject.toml ] && timeout 90 PYTHONPATH=. python -m pytest --tb=short -q --no-header 2>&1 | tail -30 || true
[ -f go.mod ]         && go test ./...
[ -f Makefile ]       && make test
```
빌드 스크립트 없으면 eslint / tsc --noEmit 등 정적 분석 실행.
빌드 실패 시 → 수정 후 재시도 (최대 2회). 2회 실패 시 BLOCK에 기록 후 계속 진행.

## Step 3.45 — PRD/Plan 동기화 (구조적 변화 시)

세션 중 다음 중 하나라도 해당하면 PRD/Plan 파일 갱신:
- 새 모듈/시스템 추가 (파일 10+ 신규)
- 아키텍처 변경 (데이터 모델, 배포 인프라, SSOT 변경)
- 핵심 기능 추가/삭제 (사용자 워크플로우 변경)
- Phase 전환

**감지**:
```bash
# 신규 파일 수 체크
NEW_FILES=$(git diff --cached --name-only --diff-filter=A 2>/dev/null | wc -l)
# 인프라 변경 체크
INFRA_CHANGE=$(git diff --cached --name-only 2>/dev/null | grep -E 'wrangler|Dockerfile|deploy|\.env|infra/' | head -1)
# PRD/Plan 파일 찾기
PLAN_FILE=$(find . .claude/plans -maxdepth 2 -name "*plan*" -o -name "*prd*" 2>/dev/null | grep -iE '\.md$' | head -1)
```

**해당 시**:
1. Plan 파일의 "구현 완료/미구현" 섹션 갱신
2. 새 아키텍처 결정 반영 (인프라, 데이터 모델 등)
3. Next Steps 업데이트

**미해당 시**: 스킵 (나레이션 없이).

## Step 3.5 — OKR 자동측정 KR 갱신 (조건부)

`.context/okr/` 디렉토리가 존재하고 최신 분기 파일이 있을 때만 실행:

```bash
OKR_DIR=".context/okr"
OKR_FILE=$(ls "$OKR_DIR/"*.md 2>/dev/null | sort | tail -1)
if [ -n "$OKR_FILE" ]; then
  echo "OKR 파일 감지: $OKR_FILE — 자동측정 KR 갱신"
  # 자동측정 가능 KR만 갱신 (수동 KR 절대 건드리지 않음)
  # 측정 소스: .context/analytics.jsonl (명령 실행 횟수), rtk gain (토큰 절감), .context/SESSIONS.md (POSTMORTEM 카운트)
  COMMAND_COUNT=$(grep -c '"type":"command_start"' .context/analytics.jsonl 2>/dev/null || echo 0)
  SESSION_COUNT=$(grep -c "^## \[" .context/SESSIONS.md 2>/dev/null || echo 0)
  echo "  명령 실행: ${COMMAND_COUNT}회 | 세션: ${SESSION_COUNT}건"
  echo "  ※ 수동 KR(매출·구독자 등)은 이 단계에서 갱신 금지 — /okr check에서 직접 입력"
else
  echo "OKR 파일 없음 — 스킵 (/okr set으로 분기 OKR 설정)"
fi
```

- **자동측정 KR**: analytics.jsonl 카운트·rtk gain·SESSIONS.md 항목수 등 파일 기반으로 파악 가능한 것만
- **수동 KR**: 매출·구독자·NPS 등 외부 측정값 — 이 단계에서 **절대 건드리지 않음** (`/okr check`에서만)
- okr.md:17 선언("세션 종료 시 OKR 파일 존재하면 진행률 자동 업데이트")과 일치

## Step 3.7 — Post-Integration 검사 (skip: HAS_ATEAM=false)
이 세션 중 `lib/*.ts`, `.claude/agents/*.md`, `governance/` 에 새 파일이 생성되었는지 확인:
```bash
git diff --cached --name-only --diff-filter=A 2>/dev/null | grep -E '^(lib/.*\.ts|\.claude/agents/.*\.md|governance/)' || true
git diff --name-only --diff-filter=A 2>/dev/null | grep -E '^(lib/.*\.ts|\.claude/agents/.*\.md|governance/)' || true
```
감지되면: PIOP Phase 1 (Integration Map) 실행.
- 미연결 항목 발견 시: 즉시 Phase 2 연결 수행 (빌드 검증 포함)
- 또는 복잡하면: CURRENT.md의 Next Tasks에 `/optimize` TODO 등록

## Step 3.8 — Commands Sync (A-Team 레포에서만, 자동)

A-Team 레포에서 `/end` 실행 시 `~/.claude/commands/`의 신규/수정 파일을 `.claude/commands/`로 자동 동기화한다.
이 단계가 없으면 Mac에서 만든 스킬이 push되지 않아 다른 PC에서 소실된다.

```bash
CURRENT_REPO=$(git rev-parse --show-toplevel 2>/dev/null || echo '')
ATEAM_CANDIDATES=(
  "$HOME/Projects/a-team"
  "$HOME/Desktop/Dev Projects/A-Team"
  "/c/Users/$USER/Desktop/Dev Projects/A-Team"
  "$CURRENT_REPO"
)

# 현재 레포가 A-Team인지 확인
IS_ATEAM=false
for candidate in "${ATEAM_CANDIDATES[@]}"; do
  [ "$(realpath "$CURRENT_REPO" 2>/dev/null)" = "$(realpath "$candidate" 2>/dev/null)" ] && IS_ATEAM=true && break
done

if $IS_ATEAM; then
  GLOBAL_CMDS="$HOME/.claude/commands"
  REPO_CMDS="$CURRENT_REPO/.claude/commands"
  mkdir -p "$REPO_CMDS"

  SYNCED=0
  while IFS= read -r -d '' f; do
    fname=$(basename "$f")
    repo_file="$REPO_CMDS/$fname"
    # 글로벌이 더 최신이거나 레포에 없으면 복사
    if [ ! -f "$repo_file" ] || [ "$f" -nt "$repo_file" ]; then
      cp "$f" "$repo_file"
      SYNCED=$((SYNCED + 1))
    fi
  done < <(find "$GLOBAL_CMDS" -maxdepth 1 -name "*.md" -print0)

  [ $SYNCED -gt 0 ] && echo "🔄 Commands sync: ${SYNCED}개 스킬 → .claude/commands/ 반영 (커밋 포함 예정)"
fi
```

## Step 3.85 — 유저 레벨 재동기화 (A-Team 레포에서만, 자동 — 2026-07-14 계위 개정 결정④)

이 세션에서 `.claude/commands/`·`.claude/agents/` 레포 파일이 수정됐으면 **역방향(레포→글로벌) 동기화 의무**:

```bash
if $IS_ATEAM; then
  CHANGED=$(git diff HEAD~5..HEAD --name-only 2>/dev/null | grep -cE '^\.claude/(commands|agents)/' || echo 0)
  if [ "$CHANGED" -gt 0 ]; then
    bash install.sh --full --force && echo "🔄 유저 레벨 재동기화 완료 (install.sh --full --force)"
  fi
fi
```

근거: 유저 레벨 drift 방지 (2026-07-14 실측 — skip-if-exists로 4일 stale + 덱 에이전트 8종 누락 → 2026-07-15 install.sh 기본 overwrite로 수리). Step 3.8(글로벌→레포)과 방향이 반대이며 둘 다 필요. Win처럼 ~/.claude가 심링크 배포인 머신에선 install.sh의 safe_cp 가드가 자동 생략 — 심링크는 항상 최신이라 재동기화 불필요 (`docs/LAYERS.md` 층위 ② 참조).

## Step 3.9 — A-Team Drift 감지 (자동)

현재 프로젝트가 a-team 자체가 **아닌데** a-team 하위 사본(`A-Team/`, `a-team/`, `.a-team/` 등)이 존재하거나, 프로젝트 내 `.claude/commands/`·`governance/`·`scripts/auto-switch/` 가 수정되었다면 drift 신호. `ateam-sovereignty.md` 제2/7원칙에 따라 **글로벌이 정본**.

```bash
CURRENT_REPO=$(git rev-parse --show-toplevel 2>/dev/null || echo '')
ATEAM_GLOBAL="$HOME/Projects/a-team"

if [ "$CURRENT_REPO" != "$ATEAM_GLOBAL" ]; then
  # 프로젝트 내 a-team 사본 수정 감지
  DRIFT_PATHS=$(git diff --name-only HEAD~20 HEAD 2>/dev/null | grep -E '^(\.?A-Team/|\.?a-team/|\.claude/commands/|governance/|scripts/auto-switch/)' || true)
  if [ -n "$DRIFT_PATHS" ]; then
    echo ""
    echo "⚠️  A-Team drift 감지 (ateam-sovereignty 제2원칙 위반 가능):"
    echo "$DRIFT_PATHS" | head -10
    echo ""
    echo "권장: 이 변경사항을 a-team 글로벌(/path/to/a-team)로 역류하세요:"
    echo "  cd $ATEAM_GLOBAL && /absorb"
    echo ""
    echo "무시하려면 다음 세션에서 계속 진행. 단 drift가 누적되면 여러 프로젝트 간 분열 발생."
  fi
fi
```

감지 시 사용자에게 1회 보고 후 세션 종료는 정상 진행. **자동 머지 안 함** (`/absorb` 스킬이 인간 결정 대기 원칙 유지).

## Step 4 — 커밋
빌드 성공 시 커밋:
```
[type]: 요약

NOW: 방금 완료한 것
NEXT: 다음 할 일
BLOCK: 막힌 점 (없으면 없음)
```

## Step 5 — 시각적 검증 (프론트엔드 작업 시)
프론트엔드 파일 수정 있으면:
- 로컬 개발 서버 URL 제공 (예: http://localhost:5173)
- 프로덕션 URL 보고 (있으면)

## Step 6 — 원격 Push (remote 없으면 자동 생성)

커밋이 있으면 **항상 즉시 실행**. 3단계 자동 처리:

### 6.0 A-Team 레포 = 양방향 브리지 (단일 push 대신)

A-Team 레포(`scripts/git-bridge.sh` 존재)면 단일 push 대신 브리지를 실행하고 6.1~6.2를 건너뛴다.
Mac→GitHub, VDI→GitLab 두-쓰기-원천을 fetch→merge→push로 수렴시킨다
(SSOT: `docs/architecture/a-team-git-sync-decision-2026-07.md`).

```bash
if [ -f "scripts/git-bridge.sh" ] && git remote get-url github >/dev/null 2>&1; then
  bash scripts/git-bridge.sh && echo "✅ Bridged: GitHub+GitLab 수렴" || echo "🔴 브리지 실패 — 출력 확인 후 재실행"
  # 브리지 성공/실패와 무관하게 6.1 이하 생략 (충돌 시 수동 해결 필요)
  SKIP_PUSH=true
fi
```

### 6.1 Remote 설정 확인
```bash
BRANCH=$(git branch --show-current)
REMOTE_URL=$(git remote get-url origin 2>/dev/null || true)

if [ -z "$REMOTE_URL" ]; then
  # Remote 미설정 → GitHub 레포 자동 생성 후 연결
  REPO_NAME=$(basename "$(pwd)")
  echo "⚠️ No 'origin' remote. Creating private GitHub repo '$REPO_NAME'..."
  gh repo create "$REPO_NAME" --private --source=. --remote=origin --push || {
    echo "❌ gh repo create 실패. 수동으로 remote 설정 후 재시도:"
    echo "   gh repo create $REPO_NAME --private --source=. --remote=origin --push"
    exit 1
  }
  echo "✅ Repo created + pushed"
  exit 0
fi
```

### 6.2 정상 Push + 에러 타입별 복구
```bash
if git push origin "$BRANCH" 2>&1 | tee /tmp/push.log; then
  echo "✅ Pushed: $BRANCH"
else
  # 에러 분류 + 자동 복구 시도
  if grep -qE "Repository not found|does not exist|not found" /tmp/push.log; then
    # Remote URL은 있지만 GitHub에 레포 없음 → 자동 생성
    REPO_NAME=$(basename "$REMOTE_URL" .git)
    ACCOUNT=$(echo "$REMOTE_URL" | sed -E 's|.*[:/]([^/]+)/[^/]+$|\1|')
    echo "⚠️ GitHub repo '$ACCOUNT/$REPO_NAME' 없음. 자동 생성..."
    gh repo create "$ACCOUNT/$REPO_NAME" --private --source=. --push || {
      echo "❌ gh repo create 실패. 수동 처리 필요"
      exit 1
    }
  elif grep -qE "rejected.*non-fast-forward|fetch first" /tmp/push.log; then
    # 원격이 앞서있음 → rebase 후 재시도
    echo "⚠️ Non-fast-forward. Rebasing..."
    git pull --rebase origin "$BRANCH" && git push origin "$BRANCH" || {
      echo "❌ Rebase 충돌. 수동 해결 필요"
      exit 1
    }
  elif grep -qE "src refspec .* does not match" /tmp/push.log; then
    echo "❌ 로컬 브랜치 '$BRANCH' 에 커밋 없음 — 비정상 상태"
    exit 1
  else
    # 네트워크/인증/기타 → 즉시 사용자 보고
    echo "❌ PUSH FAILED (unknown) — see /tmp/push.log"
    exit 1
  fi
fi
```

**원칙**: 실패 시 **절대 세션 "종료"로 처리하지 말 것** — 다른 머신에서 같은 착각 반복 금지.

## Step 6.5 — Analytics Emit (skip: HAS_LOG_EVENT=false)
세션 종료 시 analytics.jsonl에 session_end 이벤트 기록:
```bash
CMDS=$(git log --oneline -1 --format="%s" 2>/dev/null | cut -c1-60 || echo "unknown")
node "$(git rev-parse --show-toplevel 2>/dev/null)/scripts/log-event.mjs" \
  session_end \
  "summary=$CMDS" \
  "branch=$(git branch --show-current 2>/dev/null || echo unknown)" \
  2>/dev/null || true
```
실패해도 세션 종료를 막지 않음 (|| true).

## Step 6.6 — Design Learn 요약 (자동, 신규 데이터 있을 때만)

이 세션 커밋에 디자인 학습 데이터(design-scores.jsonl / user-picks.jsonl) 변경이 포함됐으면 1줄 요약 출력:

```bash
DESIGN_DATA_CHANGED=$(git diff HEAD~1 HEAD --name-only 2>/dev/null | grep -cE '(design-scores|user-picks)\.jsonl' || echo 0)
[ "$DESIGN_DATA_CHANGED" -gt 0 ] && node scripts/design-learn.mjs --brief 2>/dev/null || true
```

출력에 제안(불일치/캘리브레이션 불가 등)이 보이면 사용자에게 1줄 보고 — 강제 실행 아님. 실패해도 세션 종료를 막지 않음.

## Step 6.74 — Session Signals (자동)

세션 종료 전 세 가지 신호를 한 번에 점검한다.

```bash
ROLLBACK=$(git log --oneline -10 2>/dev/null | grep -cE "revert|rollback|undo|임시|WIP" || echo 0)
POSTMORTEM=$(ls .context/POSTMORTEM-*.md 2>/dev/null | wc -l)
LESSON_ADDED=$(git diff HEAD~1 HEAD --name-only 2>/dev/null | grep -c "MEMORY.md" || echo 0)
GROWTH_COMMITS=$(git log --grep="^growth:" --since="24 hours ago" --oneline 2>/dev/null | wc -l || echo 0)
```

- **복잡 세션 회고** (아래 중 2개 이상: 롤백 커밋, POSTMORTEM 생성, 새 레슨 추가, 좌절 표현 3회+, 같은 파일 5회+ 수정):
  이 세션의 교훈을 CLAUDE.md §5.5 라우팅으로 즉시 저장 — ENFORCE 후보는 guards 승격, 판단 규칙은 memory feedback. (/debrief는 은퇴 — 산출물이 로드 경로에 없었음)
- **Growth Loop** (그로스 커밋 3건 이상): `/growth-loop --mode=event` 실행 권장
- **레슨→훅 커버리지** (실측 — 프로즈 아님):
  ```bash
  node /path/to/a-team/scripts/lesson-coverage.mjs || echo "⚠️ 미커버 enforce 레슨 — 'node /path/to/a-team/scripts/lesson-coverage.mjs --seed'로 guards 라인 검토"
  ```
- **MEMORY.md 게이트**: `bash ~/.claude/hooks/memory-size-gate.sh < /dev/null` 출력 있으면 topic 이관 수행

강제 실행 아님(coverage/게이트 명령 실행 자체는 의무, 후속 조치는 사용자 판단).

## Step 6.8 — Command Usage Coaching (자동)

세션 중 사용된 커맨드 vs 사용 안 했지만 **썼으면 더 좋았을** 커맨드를 분석.

### 분석 기준

| 시나리오 | 놓친 커맨드 | 힌트 |
|----------|-----------|------|
| 복잡한 멀티파일 작업을 수동 진행 | `/blueprint` | 설계 문서 먼저 만들면 구현 품질 향상 |
| 큰 변경 후 wiring 확인 안 함 | `/pmi` | Post-integration 검사로 누락 방지 |
| 보안 민감 코드 수정 | `/cso` | OWASP/STRIDE 자동 감사 |
| 제품 아이디어 논의만 하고 문서화 안 함 | `/prd` 또는 `/office-hours` | 구조화된 검증 → PRD 저장 |
| 여러 접근법 고민 | `/thinking-partner` | 체계적 탐색 |
| 반복 수정 3회+ | `/tdd` | 테스트 먼저 → 재작업 방지 |
| 리뷰 없이 push | `/review` 또는 `/ship` | 품질 게이트 |
| 전략적 결정 없이 구현 | `/plan-ceo` | CEO 관점 검토 |
| 디버깅 30분+ | `/investigate` | 체계적 근본원인 분석 |
| 커버리지/성능 의문 | `/benchmark` | 기준선 측정 |

### 출력 형식

```
🎯 커맨드 활용 피드백
━━━━━━━━━━━━━━━━━━━━━
사용한 커맨드: /pickup, /prd, /plan-eng (3개)
놓친 기회:
  → /blueprint — 멀티파일 설계 선행했으면 구현 시행착오 줄었을 것
  → /pmi — 신규 파일 10개+ 추가됨, integration 검사 권장
```

3개 이하로 간결하게. 해당 없으면 생략.

### Analytics 저장

```bash
[ "$HAS_LOG_EVENT" = true ] && [ "$HAS_LOG_EVENT" = true ] && node scripts/log-event.mjs command_coaching \
  "used=pickup,prd,plan-eng" \
  "missed=blueprint,pmi" \
  2>/dev/null || true
```

## Step 6.9 — CARD.md 갱신 (자동)

⛔ 전역 브레드크럼(`~/.last-active-project.txt`) 쓰기는 폐기(2026-08-24 의장 지시) — 병렬 세션 last-writer-wins로 /pickup 오앵커의 원인이었다. 다음 세션 인계는 session-handoff 훅(SessionStart clear|startup, 터미널-로컬 전사 기반) + RESUME.md가 담당한다.

```bash
CURRENT_REPO=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
BRANCH=$(git branch --show-current 2>/dev/null || echo "none")
LAST=$(git log -1 --oneline 2>/dev/null || echo "none")
if [ -d "$CURRENT_REPO/.context" ]; then
  echo "BRANCH: $BRANCH | LAST: $LAST"
fi
```

그 다음, Claude가 이번 세션 작업 내용을 반영해 `$CURRENT_REPO/.context/CARD.md`를 5줄로 갱신:
- `PROJECT:` 프로젝트명
- `TASK:` 이번 세션에서 작업/완료한 것
- `STATUS:` 현재 상태 (배포됨/진행중/대기)
- `NEXT:` 다음 세션 첫 번째 액션
- `BRANCH: X | LAST: Y (커밋메시지 앞 20자)`

실패해도 세션 종료를 막지 않음. 다음 `/focus`가 CARD.md를 읽어 ~50토큰으로 복원.

## Step 7 — (선택) Research Mode
자리를 오래 비울 예정이면 "Research Mode를 시작할까요?" 질문.
원하면: `/re start`
