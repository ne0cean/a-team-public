---
description: /qa — 웹 앱 체계적 QA 테스트
---

> Analytics: `node scripts/log-event.mjs command_start name=qa` — 실행 시작 시 반드시 호출

`qa` 서브에이전트(subagent_type="qa")를 호출하여 실행하세요.

- 사용자 인자(URL, --pages, --category)가 있으면 그대로 전달
- 에이전트 완료 후 헬스 스코어와 이슈 목록을 사용자에게 요약 보고
- CRITICAL 이슈는 반드시 강조
- claude-remote 프로젝트이면 마지막에 1줄 추가: "WS/터미널 검증: `/ws-qa` 실행 권장"

## Codex/Gemini fallback

Claude `Task` 또는 `subagent_type`을 사용할 수 없는 런타임에서는
`.claude/agents/qa.md`를 실행 체크리스트로 읽고 네이티브 브라우저/Playwright 도구로 직접 수행한다.

1. URL 결정: 사용자 인자, 프로젝트 문서의 local/staging/prod URL, 실행 중인 dev server 순서로 확인한다.
2. 스냅샷: desktop/mobile/tablet 중 최소 2개 뷰포트에서 스크린샷과 콘솔 에러를 수집한다.
3. 핵심 흐름: 변경 범위와 연결된 사용자 플로우를 최소 1개 실행한다.
4. 이슈 분류: CRITICAL/HIGH/MEDIUM/LOW로 나누고 재현 단계와 증거 파일을 남긴다.
5. 재검증: CRITICAL 또는 HIGH를 수정했다면 같은 플로우를 다시 실행한다.

완료 보고에는 헬스 스코어, CRITICAL/HIGH 개수, 확인 URL, 실행한 검증 명령,
스크린샷/리포트 경로를 포함한다.

## `--design` 플래그 (자동 체이닝)

인자에 `--design` 포함 또는 변경 파일이 `.tsx/.jsx/.vue/.svelte/.css/.scss` 중심이면 자동으로:
1. `qa` + `ui-inspector` + `design-auditor` 3개 서브에이전트를 **병렬** 호출
2. 결과 머지:
   - ui-inspector 시각 findings + design-auditor 점수/위반 + qa 헬스 스코어
   - a11y 위반은 최상위 우선순위 (비협상)
3. `lib/analytics.ts` `logDesignAudit()` 기록
4. 최종 리포트: `점수 N/100, A11y X건, AI Slop Y건, Layout Z건 → 종합 헬스 H/100`

`governance/design/gate.md` 의 opt-out 규칙 존중 — `design: off` 또는 `exemptions` 매치 시 design-auditor 스킵.
