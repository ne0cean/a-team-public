---
description: /tdd — TDD Red-Green-Refactor 루프
---

> Analytics: `node scripts/log-event.mjs command_start name=tdd` — 실행 시작 시 반드시 호출

`tdd` 서브에이전트(subagent_type="tdd")를 호출하여 실행하세요.

- 구현할 기능 설명을 그대로 전달
- 에이전트가 RED→GREEN→REFACTOR 단계를 순차 실행
- 에이전트 완료 후 테스트 결과를 사용자에게 요약 보고

## Codex/Gemini fallback

Claude `Task` 또는 `subagent_type`을 사용할 수 없는 런타임에서는
`.claude/agents/tdd.md`를 실행 체크리스트로 읽고 네이티브 도구로 직접 수행한다.

1. RED: 변경 요구를 한 문장으로 고정하고 실패해야 하는 테스트를 먼저 추가한다.
2. RED 검증: 해당 테스트만 실행해 실패 원인이 기대한 미구현 상태인지 확인한다.
3. GREEN: 테스트를 통과시키는 최소 구현만 한다.
4. GREEN 검증: 관련 테스트를 재실행한다.
5. REFACTOR: 테스트를 바꾸지 않고 구조만 정리한 뒤 관련 테스트와 빌드를 재실행한다.

완료 보고에는 최소한 `red_passed`, `green_passed`, `refactor_passed`,
추가/수정 테스트 파일, 실행한 검증 명령을 포함한다.
