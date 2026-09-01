# Codex Task Brief — <task-slug>

> 템플릿 사용법: 전 필드 필수. 150줄 이하 유지. 기계 검증 명령(Verification
> Gates)이 하나도 없으면 외주하지 않는다 — 검증 불가능한 작업은 위임 대상이 아니다.

## Task

<한 문단: 무엇을 만드는가. 왜가 아니라 무엇 중심으로 구체적으로.>

## Files (소유권 — 이 목록 밖 수정 금지)

- `path/to/new-file.ts` — 신규
- `path/to/existing.ts` — 수정 (해당 함수만)

## Signatures / Interfaces

```ts
// 구현할 공개 인터페이스를 먼저 고정한다 (volatile 결정 선두 원칙)
export function example(input: Foo): Bar
```

## Requirements

1. <기능 요구 1>
2. <기능 요구 2>

## Constraints

- <금지 사항: 예. 외부 의존성 추가 금지, 특정 디렉토리 no-touch>
- 기존 코드 스타일(주변 코드의 네이밍·주석 밀도) 준수

## Verification Gates (기계 게이트 — 전부 exit 0이어야 완료)

```bash
npx tsc --noEmit
npx vitest run test/<관련 테스트>
# 필요 시: grep 기반 구조 확인
```

## Branch / Dispatch

- Branch: `codex/<YYYY-MM-DD>-<slug>`
- Dispatch: local (pumasi) | cloud (`codex cloud exec --env <ENV_ID>`) | github
- Commit trailer: `Co-Authored-By: Codex`

## Done Definition

- 모든 게이트 exit 0 + diff가 Files 소유권 내 + Claude reviewer PASS 후 머지 (리뷰 생략 금지)
