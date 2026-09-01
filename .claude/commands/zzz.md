---
description: /zzz — 풀 오토 수면 모드 (하던 작업을 이어서 계속, 토큰 리셋 자동 이어받기)
---

> Analytics: `node scripts/log-event.mjs command_start name=zzz` — 실행 시작 시 반드시 호출

# /zzz — 풀 오토 수면 모드

> **약속**: 지금 하던 작업을 그대로 이어서 계속. 질문 0, 나레이션 0, 토큰 소진까지 진행. 리셋되면 자동 이어받기.
> **계약**: `governance/rules/autonomous-loop.md` (단일 계약 — 조항 1-9 + Git Backup + AGENT_STATUS). 진입 시 반드시 Read.
> **구조**: 2층 — ①세션 생존 중 네이티브 dynamic loop(ScheduleWakeup) ②세션 사망 시 launchd 백스톱(`com.ateam.sleep-resume-all`, 120초 폴링)이 RESUME.md 게이트로 재개.

---

## 자동 트리거
수면 의도 ("자러간다"/"잘게") + 자율 의도 ("랄프 모드"/"알아서 해") 양쪽 1개씩 → 확인 없이 진입.

## 수동 호출
- `/zzz` — 하던 작업 이어서 풀-오토
- `/zzz --ide` — IDE 반-자동 (사용자 클릭 진행, 나레이션 1500 bytes)
- `/zzz --fresh <태스크>` — 새 태스크 큐 (예외)
- `/zzz --check` — infra 점검만

---

## Step 1 — 진입 게이트 (CLI 검증 + 인프라)

풀-오토는 CLI `--dangerously-skip-permissions` 필수. 부모 프로세스 args에서 확인:

```bash
node scripts/log-event.mjs command_start name=zzz
PID=$$; CLAUDE_ARGS=""
for _ in 1 2 3 4 5 6; do
  PARENT=$(ps -p "$PID" -o ppid= 2>/dev/null | tr -d ' ')
  [ -z "$PARENT" ] || [ "$PARENT" = "0" ] || [ "$PARENT" = "1" ] && break
  ARGS=$(ps -o args= -p "$PARENT" 2>/dev/null)
  echo "$ARGS" | grep -qE "(^|/)claude(\s|$)" && { CLAUDE_ARGS="$ARGS"; break; }
  PID=$PARENT
done
echo "$CLAUDE_ARGS" | grep -qE -- "--dangerously-skip-permissions|--permission-mode bypassPermissions"
```

- 통과 → 계속. `acceptEdits` + `--ide` → 반-자동. 그 외 → 종료 + `claude --dangerously-skip-permissions` 재진입 안내.

인프라 체크 (5초):
```bash
bash /path/to/a-team/scripts/zzz-permission-toggle.sh on
launchctl list | grep com.ateam.sleep-resume-all || { cp scripts/launchd/com.ateam.sleep-resume-all.plist ~/Library/LaunchAgents/ 2>/dev/null; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ateam.sleep-resume-all.plist; }
launchctl list | grep com.ateam.auto-switch || bash scripts/install-auto-switch-cron.sh install
rm -f ~/.ateam-sleep-locks/last-success ~/.ateam-sleep-locks/running.pid
claude -p --model haiku --max-budget-usd 0.10 "ok" 2>&1 | head -3
```

프로브 실패 → 진입 중단 + 원인 보고 (조항 7: 미검증 인프라에 수면 허락 금지).

## Step 2 — RESUME.md 하드 게이트 (다른 무엇보다 먼저)

**이 파일이 안 쓰이면 백스톱은 발화하지 못한다.** wakeup 예약·작업 시작 전에 반드시 먼저 기록:

```markdown
---
mode: zzz
entered_at: <ISO>
next_reset_at: <ISO — 사용자 명시 → /usage 패턴 → 기본 5시간>
contract: autonomous-loop.md
status: in_progress
session_goal: "<현재 작업 1-2문장>"
---
## In Progress
- [ ] <진행 중이던 것>
## Completed This Session
- [x] <커밋한 것들>
## Next Immediate Step
<바로 해야 할 1개 액션>
## Files Touched
<파일 경로>
```

게이트 규칙: `mode: zzz` + `status: in_progress` 둘 다 없으면 launchd 디스패처가 SKIP한다 (`sleep-resume.sh` 실측). `[결정필요]` 마커가 있으면 그 항목은 픽업 대상에서 제외됨.

## Step 3 — Dynamic Loop 시작

CronCreate 금지 (session-only, 디스크 미기록 — 2026-07-04 실측). 대신 **네이티브 dynamic loop**:

- 턴 시작마다 ScheduleWakeup 선-예약 (조항 2). 일반 작업 간격: 1200–1800초.
- 세션이 살아있는 동안 wakeup이 루프를 지속. 세션이 죽으면 launchd 백스톱이 RESUME.md 게이트로 이어받는다 — 추가 조치 불필요.
- 진입 1줄 출력 후 즉시 작업 재개 (이후 나레이션 ≤500 bytes):
```
🌙 zzz 모드 진입 | 리셋: <HH:MM> | 진행: <session_goal>
```

## Step 4 — 진행 중 동작

- 토큰 소진까지 무정지. 매 commit 후 RESUME.md 갱신.
- **Git Backup / Circuit Breaker / Dual-Exit**: autonomous-loop.md 그대로 (backup stash → CB: no_progress 3회·same_error 5회 → dual-exit `exit_recommended: true`, 자동 종료 안 함).
- **Usage-Window Throttle**: 매 wave 전 `npx -y ccusage@latest blocks --active --json` 잔량 조회 → 95% 도달 시 commit+push 후 일시정지, RESUME.md에 pause 기록.
- **작업 픽업**: session_goal 내 다음 sub-step → 소진 시 CURRENT.md Next Tasks 안전 항목 (`rule`/`test`/`doc`/`refactor`/`lint`/`cleanup`). 제외: `사용자 결정 대기`, `[HUMAN INSERT]`, `prod`, `deploy`, `force`, `migrate`, OAuth, API 키.
- 모든 명시 태스크 소진 → `/daily-brief` (scan+apply) 자동 실행.
- 토큰 한계 → commit + push + RESUME.md 저장 → 백스톱 이어받음. 재개 성공의 유일한 증거 = 재개 세션이 만든 커밋 해시.
- 작업 에러 2회 재시도 → Blockers 기록 + 다음 진행. CLI 인증 실패 → `claude login` 안내 후 대기.

## Step 5 — 아침 보고

≤10줄: 경과/cycle/commit 수 + 완료/차단 + 다음 1줄 + AGENT_STATUS 블록. 그리고 **반드시**:
```bash
bash /path/to/a-team/scripts/zzz-permission-toggle.sh off
```
(off 누락 = 전역 bypass 잔존. `~/.ateam/zzz-active` 마커 없는데 bypass가 켜져 있으면 즉시 off.)

---

## 관계도
```
/zzz  → 하던 거 이어서 (RESUME.md 게이트 + dynamic loop + launchd 백스톱)
/goal → 기계 검증 목표 루프 (인세션, --check 통과까지)
/resume → 리셋 재개만 (자율 없음)
/pickup → 재개 실행 공통 (RESUME.md mode: zzz + status != completed 감지 → In Progress부터)
```
