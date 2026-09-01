---
description: 세션 재개 기본 진입점 — 상황 자동 감지 후 경량 복구 또는 /vibe 분기
---

> **기본 진입점**: 세션이 끊겼을 때 무조건 `/pickup` 사용.
> 내부에서 상황 판단 → 작업 흔적 있으면 경량 복구, 없으면 /vibe 제안.

## Step 0.0 — 현재 터미널 마지막 작업 확정 (터미널-로컬 우선)

⛔ **전역 `~/.last-active-project.txt` 참조 금지** — 다른 터미널·다른 날 작업으로 점프하는 원인 (2026-08-24 의장 지시: pickup은 항상 **현재 터미널**의 마지막 작업만 이어받는다).

**0순위 — 세션 인계 컨텍스트**: 세션 시작 시 `🔗 직전 세션 인계` system-reminder가 있으면(session-handoff 훅, clear|startup 발화) **그 전사가 이어받을 세션이다**. 발화 요지로 프로젝트/스레드를 판별하고, 모호(⚠️ 병렬 세션)하면 전사 tail을 직접 읽어 확정한다. repo 프로젝트로 판별되면 그 경로를 `/tmp/.pickup-project-root`에 쓰고 아래 bash 결과를 덮어쓴다.

```bash
CURRENT_DIR=$(pwd)
PROJECT_ROOT=""

# ① cwd 자체가 프로젝트면 즉시 확정 (이 터미널이 프로젝트 안에서 작업 중)
if git -C "$CURRENT_DIR" rev-parse --show-toplevel >/dev/null 2>&1 || [ -d "$CURRENT_DIR/.context" ]; then
  PROJECT_ROOT=$(git -C "$CURRENT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$CURRENT_DIR")
  echo "📁 현재 디렉토리 프로젝트: $PROJECT_ROOT"
else
  # ② 현재 터미널의 직전 세션 전사에서 마지막 작업 추출 (같은 cwd 슬러그 폴더)
  WINPWD=$(cygpath -w "$CURRENT_DIR" 2>/dev/null || echo "$CURRENT_DIR")
  SLUG=$(printf '%s' "$WINPWD" | sed 's/[^a-zA-Z0-9]/-/g')
  PREV=$(ls -t "$HOME/.claude/projects/$SLUG"/*.jsonl 2>/dev/null | sed -n '2p')  # 1위=현재 세션, 2위=직전 세션
  if [ -n "$PREV" ]; then
    PREV_CWD=$(tail -c 100000 "$PREV" | grep -o '"cwd":"[^"]*"' | tail -1 | sed 's/^"cwd":"//;s/"$//' | tr '\\' '/' | tr -s '/')
    echo "🔎 직전 터미널 세션 전사: $PREV"
    echo "   직전 작업 cwd: $PREV_CWD"
  else
    echo "🔎 직전 터미널 세션 없음"
  fi
fi
[ -z "$PROJECT_ROOT" ] && PROJECT_ROOT="$CURRENT_DIR"
echo "$PROJECT_ROOT" > /tmp/.pickup-project-root
echo "PROJECT_ROOT=$PROJECT_ROOT"
```

**② 분기 후속 (PREV가 있을 때 의무)**: 직전 전사 tail(마지막 30~50줄)을 읽어 **직전 작업 요지**를 파악한다. `PREV_CWD`가 git repo면 그 toplevel을 `/tmp/.pickup-project-root`에 덮어쓴다. 직전 전사의 작업이 현 cwd와 다른 프로젝트여도 **그것이 이어받을 작업이다** — 단 근거는 항상 이 터미널의 직전 전사이지, 전역 파일이 아니다. 직전 전사도 없으면 흔적 없음 → Step 0의 /vibe 분기.

**중요**: 이하 모든 Step에서 `.context/` 경로 참조 및 `git` 명령은 `$PROJECT_ROOT` 기준 절대경로를 사용한다.
- `.context/RESUME.md` → `$PROJECT_ROOT/.context/RESUME.md`
- `git status` → `git -C $PROJECT_ROOT status`
- `git log` → `git -C $PROJECT_ROOT log`

---

## Step 0 — 작업 흔적 감지 (자동 분기)

```bash
PROJECT_ROOT=$(cat /tmp/.pickup-project-root 2>/dev/null || pwd)
node scripts/log-event.mjs command_start name=pickup
# 1. RESUME.md 존재 + 미완료?
RESUME_ACTIVE=""
[ -f "$PROJECT_ROOT/.context/RESUME.md" ] && ! grep -q "status:.*completed" "$PROJECT_ROOT/.context/RESUME.md" && RESUME_ACTIVE="1"

# 2. git에 uncommitted 변경?
GIT_DIRTY=$(git -C "$PROJECT_ROOT" status --porcelain 2>/dev/null | head -1)

# 3. CURRENT.md에 In Progress Files?
IN_PROGRESS=""
[ -f "$PROJECT_ROOT/.context/CURRENT.md" ] && \
  IN_PROGRESS=$(awk '/^## In Progress Files/,/^## /' "$PROJECT_ROOT/.context/CURRENT.md" 2>/dev/null | grep -vE "^##|없음|\(없음\)" | grep -v "^$" | head -1)

# 4. .context/checkpoints/ 에 활성 체크포인트?
CHECKPOINTS=""
mkdir -p "$PROJECT_ROOT/.context/checkpoints/archive" 2>/dev/null
CHECKPOINTS=$(ls "$PROJECT_ROOT/.context/checkpoints"/*.json 2>/dev/null | grep -v archive | head -1)

# 판정
if [ -n "$RESUME_ACTIVE" ] || [ -n "$GIT_DIRTY" ] || [ -n "$IN_PROGRESS" ] || [ -n "$CHECKPOINTS" ]; then
  echo "✅ 작업 흔적 감지 — 경량 복구 진행"
else
  echo "📭 작업 흔적 없음 — 새 세션입니다. /vibe 실행할까요? (Y/n)"
  # 사용자가 Y 또는 Enter → /vibe 실행
  # N → 빈 상태로 시작
fi
```

**분기 결과**:
- 흔적 있음 → Step 1~4 경량 복구 진행
- 흔적 없음 → 사용자에게 `/vibe` 제안 (1줄), 거절 시 빈 상태 시작

---

## Step 0.5 — Scheduled Reviews + DISTILL + 온톨로지 의결 큐

```bash
node /path/to/a-team/scripts/check-scheduled-reviews.mjs 2>/dev/null || true
node /path/to/a-team/scripts/check-distill-triggers.mjs 2>/dev/null || true
# 온톨로지 피드백 루프: 리뷰 재생성 후 의장 대기 의결 수 브리핑 (7일 경과 시에만 재생성 — 매 pickup 비용 방지)
node /path/to/a-team/scripts/ontology.mjs review 2>/dev/null | tail -1 || true
grep -c "의장 결정\*\*: (대기)" /path/to/a-team/.context/ontology/REVIEW.md 2>/dev/null || true
```
- due 항목 있음 → 브리핑에 포함 + "예약 리뷰 N건 도래" 안내
- **온톨로지 의결 대기 ≥1** → 브리핑에 "온톨로지 의결 N건 대기 (`.context/ontology/REVIEW.md`)" 1줄 — HIGH 항목은 요지도 1줄. 의장 결정 수신 시 해당 실행 커맨드로 Act 후 REVIEW.md 결정란 갱신
- due 항목 없음 → 스킵
- DISTILL P1 후보 있음 → 브리핑에 "bespoke 패턴 승격 후보 N건" 1줄 포함

---

## Step 1 — 상태 확인 (흔적 있을 때만)

```bash
git log --oneline -5
git status --short
git diff --stat HEAD~1 2>/dev/null | tail -5
```

## Step 1.5 — Heartbeat 9-Check (Paperclip Pattern 5)

빠르게 9항목 점검 — 상태 한 줄씩 출력:

```bash
PROJECT_ROOT=$(cat /tmp/.pickup-project-root 2>/dev/null || pwd)
# 1. RESUME.md 미완료?
[ -f "$PROJECT_ROOT/.context/RESUME.md" ] && ! grep -q "status:.*completed" "$PROJECT_ROOT/.context/RESUME.md" \
  && echo "HB1: RESUME active" || echo "HB1: RESUME clear"

# 2. git dirty 파일 수
DIRTY=$(git -C "$PROJECT_ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
echo "HB2: git dirty=${DIRTY} files"

# 3. In Progress Files 유무
IN_PROG=$(awk '/^## In Progress Files/,/^## /' "$PROJECT_ROOT/.context/CURRENT.md" 2>/dev/null \
  | grep -vE "^##|없음|\(없음\)" | grep -v "^$" | wc -l | tr -d ' ')
echo "HB3: in_progress=${IN_PROG} files"

# 4. 마지막 커밋 이후 경과
LAST_COMMIT=$(git -C "$PROJECT_ROOT" log -1 --format="%ar" 2>/dev/null || echo "unknown")
echo "HB4: last_commit=${LAST_COMMIT}"

# 5. 마지막 알려진 테스트 상태 (CURRENT.md 빌드 섹션)
TEST_LINE=$(grep -m1 "tests PASS\|test.*pass\|PASS\|✅" "$PROJECT_ROOT/.context/CURRENT.md" 2>/dev/null | head -c 60 || echo "unknown")
echo "HB5: last_test=${TEST_LINE}"

# 6. Blockers 변경 여부
BLOCKERS=$(grep -c "^\- \[BLOCKED\]" "$PROJECT_ROOT/.context/CURRENT.md" 2>/dev/null || echo 0)
echo "HB6: blockers=${BLOCKERS}"

# 7. CURRENT.md 갱신 필요 (오늘 날짜 포함 여부)
TODAY=$(date +%Y-%m-%d)
grep -q "$TODAY" "$PROJECT_ROOT/.context/CURRENT.md" 2>/dev/null \
  && echo "HB7: CURRENT.md today=yes" || echo "HB7: CURRENT.md today=no (갱신 필요 가능성)"

# 8. a-team-absorbed 변경 여부
ABSORBED_DIRTY=$(git -C /path/to/a-team-absorbed status --porcelain 2>/dev/null | wc -l | tr -d ' ')
echo "HB8: absorbed_dirty=${ABSORBED_DIRTY}"

# 9. Cloudflare 배포 상태 (마지막 배포 기록)
DEPLOY_LINE=$(grep -m1 "Version:\|배포\|deploy" "$PROJECT_ROOT/.context/CURRENT.md" 2>/dev/null | head -c 80 || echo "unknown")
echo "HB9: last_deploy=${DEPLOY_LINE}"
```

해석:
- HB2 dirty > 10 → uncommitted 작업 대량 존재, 커밋 우선
- HB3 > 0 → In Progress 작업 있음, 파일 읽고 재개
- HB6 > 0 → 블로커 확인 후 우회 방법 검토
- HB7 today=no → CURRENT.md 오래됐음, 세션 후 갱신 권장

## Step 2 — 컨텍스트 로드

`PROJECT_ROOT=$(cat /tmp/.pickup-project-root 2>/dev/null || pwd)` 로 경로 확인 후 다음 파일을 순서대로 읽는다:

1. **`$PROJECT_ROOT/.context/RESUME.md`** — 최우선. 존재 + `status != completed` 이면 sleep-mode 재개 포인트
2. `$PROJECT_ROOT/.context/CURRENT.md` — 현재 상태 / In Progress / Next Tasks / Blockers
3. `$PROJECT_ROOT/memory/MEMORY.md` — 프로젝트 패턴 및 규칙
4. `$PROJECT_ROOT/CLAUDE.md` — 거버넌스 규칙 (있으면)
5. **`$PROJECT_ROOT/.context/checkpoints/`** — 활성 체크포인트 (있으면): `ls $PROJECT_ROOT/.context/checkpoints/*.json 2>/dev/null | grep -v archive | sort -r | head -3` 로 최신 3개 확인 후 가장 최근 파일 Read. `status: in_progress` 항목이 있으면 `resume_prompt` 참조해 재개 우선.

## Step 2.5 — Zzz-Mode 감지 (자동, 과거 Sleep-Mode)

`.context/RESUME.md` frontmatter 에 `mode: zzz` (또는 legacy `sleep`) + `status != completed` 확인 시:
- `governance/rules/autonomous-loop.md` **의무 Read** (6개 강제 조항, 특히 **조항 6 나레이션 금지**)
- RESUME.md `Completed` 섹션 파싱 → 중복 실행 방지
- `next_wakeup_scheduled` 있으면 OS-level launchd 살아있는지 확인 (`launchctl list | grep com.ateam.sleep-resume`)
- `In Progress` 부터 재개, 사용자 대상 텍스트 최소화

## Step 2.7 — Daily Growth Brief 확인

```bash
TODAY=$(date +%Y-%m-%d)
[ -f ".context/briefs/${TODAY}-brief.md" ] && echo "BRIEF_EXISTS" || echo "NO_BRIEF"
```

- `NO_BRIEF` + 일반 pickup (zzz 아님) → 1줄 제안: "`/daily-brief` 로 오늘 성장 브리핑을 받아보세요"
- `BRIEF_EXISTS` → Executive Summary 1줄 표시 후 재개
- zzz/sleep 모드 → 스킵 (나레이션 금지)

## Step 3 — 재개

- `In Progress Files` (CURRENT.md) 또는 `In Progress` (RESUME.md) 에 파일이 있으면: 해당 파일을 읽고 중단된 작업 파악
- `Next Tasks` 최우선 항목을 즉시 시작
- 브리핑 없이 바로 실행
- sleep-mode이면 첫 액션 전에 "어디서 이어받는지" 보고 **금지** (조항 6)
- 일반 pickup이면 한 줄로만 보고

## Step 4 — CURRENT.md 갱신

작업 재개 후 CURRENT.md의 `In Progress Files`를 현재 상태로 업데이트.
