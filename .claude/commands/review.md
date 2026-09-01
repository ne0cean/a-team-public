---
description: /review — Pre-Landing PR 리뷰 파이프라인
---

```bash
node scripts/log-event.mjs command_start name=review
```

`review-pr` 서브에이전트(subagent_type="review-pr")를 호출하여 실행하세요.

- 사용자 인자가 있으면 그대로 전달
- 에이전트 완료 후 결과를 사용자에게 요약 보고
- CRITICAL/HIGH 이슈가 있으면 반드시 강조

## Design Gate (UI PR 자동 체크)

PR에 UI 파일 변경 (`*.tsx/.jsx/.vue/.svelte/.css/.scss`) 포함 시:
1. `design-auditor` 서브에이전트 자동 호출 with `gate_context: 'ship'` (threshold 70, a11y 0)
2. `governance/design/gate.md` opt-out 규칙 존중 (`.design-override.md` `design: off` / `exemptions` 매치 시 스킵)
3. 실패 시: a11y 위반은 CRITICAL로 리포트. AI slop HIGH는 차단 사유.
4. 결과는 review-pr 리포트의 "Design Audit" 섹션에 통합.
