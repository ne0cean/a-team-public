---
description: "PR 생성 전 완전 검증"
---

# /ship — PR 생성 전 완전 검증 파이프라인

PR 생성 전 자동화된 품질 게이트를 순서대로 실행한다.
사용자 개입 없이 자동 실행, 판단이 필요한 지점에서만 멈춘다.

## 사전 조건
- feature 브랜치에 있을 것 (main/master에서 실행 시 즉시 중단)
- 커밋되지 않은 변경사항 있어도 OK (자동 포함)

---

## Step 1: 사전 검사
```bash
node scripts/log-event.mjs command_start name=ship
# 브랜치 확인
BRANCH=$(git branch --show-current)
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "ABORT: main/master 브랜치에서 ship 금지"
  exit 1
fi

# 베이스 브랜치 감지
git fetch origin
BASE=$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD origin/master)
```

## Step 2: 업스트림 병합
```bash
git merge origin/main --no-edit 2>/dev/null || git merge origin/master --no-edit
# 충돌 시: 즉시 중단, AskUserQuestion으로 해결 방법 확인
```

## Step 3: 테스트 실행
```bash
# CLAUDE.md에서 테스트 명령 읽기, 없으면 기본값 사용
npm test 2>&1 | tail -20
```

**실패 분류**:
- **이번 PR 원인**: 수정 후 재시도
- **기존 실패**: AskUserQuestion → [수정/TODO 추가/스킵] 선택

## Step 4: 커버리지 감사
변경된 파일의 코드 경로를 ASCII 다이어그램으로 매핑:
```
[함수명] → [경로 A] ✓ 테스트 있음
         → [경로 B] ✗ 테스트 없음 ← 자동 생성 대상
```
단순 unit test 갭 → 자동 생성
E2E/복잡한 테스트 갭 → AskUserQuestion

## Step 5: 문서 Drift 빠른 체크
`/doc-sync --quick` 실행 (BROKEN 항목만 — 존재하지 않는 함수/경로 참조).
- BROKEN 항목 발견 시 → 자동 수정 후 계속
- 수정 불가 항목 → AskUserQuestion

## Step 5.8: Diff Sanity Gate
```bash
bash scripts/quality-gate-stage2.sh staged
```
- exit 1 (BLOCK) → 즉시 ship 중단, 위반 내용 출력
- exit 2 (WARN) → AskUserQuestion (진행/스킵 선택)
- exit 0 → 계속

## Step 5.5: Design Gate (UI 변경 감지 시 자동)
변경 파일에 `*.tsx/.jsx/.vue/.svelte/.css/.scss` 포함 시:
```bash
# .design-override.md opt-out 체크
grep -q "^design:\s*off" .design-override.md 2>/dev/null && echo "Design gate disabled" || \
  # design-auditor 서브에이전트 호출 (gate_context: 'ship', threshold 70, a11y 0)
  echo "Running design audit..."
```
- a11y 위반 1건이라도 있으면 **즉시 차단** (비협상)
- 점수 < 70 → AskUserQuestion (수정/override/스킵)
- `governance/design/gate.md` 규칙 따름

## Step 6: Pre-landing 리뷰
reviewer 에이전트 호출 (2-pass 체크리스트).
- APPROVED / APPROVED_WITH_CONCERNS → 계속
- REJECTED → 수정 후 재시도 (최대 1회)
- 2회 REJECTED → AskUserQuestion

## Step 7: 버전 범프
```bash
git log $BASE..HEAD --oneline | head -20
```
- breaking change 있음 → AskUserQuestion (MINOR/MAJOR 확인)
- 없음 → PATCH 자동 선택

## Step 8: 커밋 & PR 생성
```bash
# A-Team 커밋 형식 사용
git add -p  # 변경사항 확인
git commit -m "[type]: 요약

NOW: 완료 내용
NEXT: 다음 작업
BLOCK: none"

git push origin $BRANCH

# PR 생성
gh pr create \
  --title "[type]: 요약" \
  --body "## 변경 내용
[what/why]

## 테스트
- [ ] 테스트 통과
- [ ] 리뷰어 승인

## 체크리스트
- [ ] Breaking change 없음 (있으면 명시)
- [ ] 문서 업데이트 필요 없음 (필요하면 링크)"
```

## 자동 중단 조건 (AskUserQuestion 필요)
1. main/master 브랜치 감지
2. 머지 충돌
3. 이번 PR 원인 테스트 실패
4. doc-sync BROKEN 항목 자동 수정 불가
5. MINOR/MAJOR 버전 범프 필요
6. reviewer 2회 REJECTED

## 완료 출력
```
PR URL: [링크]
status: DONE | DONE_WITH_CONCERNS
```
