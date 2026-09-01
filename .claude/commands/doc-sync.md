---
description: /doc-sync — 문서 Drift 감지 & 동기화
---

> Analytics: `node scripts/log-event.mjs command_start name=doc-sync` — 실행 시작 시 반드시 호출

`doc-sync` 서브에이전트(subagent_type="doc-sync")를 호출하여 실행하세요.

- 사용자 인자(--quick 등)가 있으면 그대로 전달
- 에이전트 완료 후 문서 건강도 점수와 drift 목록을 사용자에게 요약 보고
- BROKEN 항목은 반드시 강조
