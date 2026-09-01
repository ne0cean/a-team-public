---
description: 전체 프로젝트 현황 — 각 레포의 .context/CURRENT.md에서 상태와 다음 태스크를 수집해 출력
---

GitHub 레포 전체를 순회하며 각 레포의 `.context/CURRENT.md`에서 프로젝트 현황을 수집해 출력하라.

## Step 0 — 메모 출력 (최상단)

`$HOME/.claude/todo-memos.md` 파일을 읽는다.

미완료 항목(`- [ ]`)이 1개 이상 있으면 프로젝트 목록보다 먼저 출력:

```
📌 메모
 1. [내용] · [날짜]
 2. [내용] · [날짜]
─────────────────────────────
```

미완료 항목이 없으면 이 섹션을 생략한다.

## Step 1 — 레포 목록 수집

```bash
gh api user --jq .login
gh repo list --limit 100 --json name,updatedAt,isArchived --jq '[.[] | select(.isArchived == false)] | sort_by(.updatedAt) | reverse | .[].name'
```

## Step 2 — 각 레포에서 CURRENT.md 가져오기

각 레포명에 대해:
```bash
gh api repos/{owner}/{repo}/contents/.context/CURRENT.md --jq '.content' | base64 -d
```

CURRENT.md가 없는 레포는 README.md에서 description 첫 줄만 가져온다:
```bash
gh api repos/{owner}/{repo}/contents/README.md --jq '.content' | base64 -d | head -5
```

## Step 3 — 파싱 규칙

CURRENT.md에서 추출:
- **상태**: `## 📍 상태` 섹션의 값 (없으면 `## Status` 섹션)
- **다음 태스크**: `## 🚀 다음 할 일` 섹션의 첫 번째 미완료 항목 `- [ ]` (없으면 첫 번째 항목)
- **마지막 작업일**: `## ✅ 마지막 완료 내역 [날짜]` 에서 날짜 추출

CURRENT.md가 없는 레포:
- **상태**: `문서 없음`
- **다음 태스크**: README 첫 줄 또는 repo description

## Step 4 — 태스크 분류

수집한 "다음 할 일" 항목들을 아래 기준으로 분류한다.

**🔵 Claude Opus (고난이도)** — 다음 중 하나에 해당:
- 아키텍처 설계, 리팩토링, 시스템 설계 결정
- 복잡한 버그 디버깅, 멀티파일 연쇄 변경
- 새 기능 설계 및 구현 (비즈니스 로직 포함)
- 에이전트/AI 파이프라인 구축
- 보안·성능 최적화

**🟡 Gemini (단순 처리)** — 다음 중 하나에 해당:
- 문서 작성, README 업데이트, 주석 추가
- 단순 반복 작업, 데이터 변환, 포맷 정리
- UI 텍스트/복사 수정, 스타일 조정
- 테스트 케이스 추가 (로직 변경 없음)
- 설정 파일 수정, 환경변수 정리
- 리서치, 레퍼런스 조사

## Step 5 — 출력 형식

최근 업데이트 순으로 출력 (updatedAt 기준):

```
1. **{레포명}** [{마지막작업일}] — {상태}
   🔵 Opus: {고난이도 태스크 1가지}
   🟡 Gemini: {단순 태스크 1가지}
```

CURRENT.md가 없는 레포는 별도 섹션으로 묶어 마지막에 출력:
```
📭 문서 없는 레포: repo1, repo2, repo3
```

모든 레포 출력 후:
```
---
총 N개 프로젝트 | CURRENT.md 있음: N개 / 없음: N개
🔵 Opus 태스크 총 N건 | 🟡 Gemini 태스크 총 N건
```

## 서브커맨드

`/prjt {레포명}` — 해당 레포의 CURRENT.md 전체 내용을 요약하고, 전체 태스크를 Opus/Gemini로 분류해 출력
