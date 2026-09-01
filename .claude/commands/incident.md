---
description: /incident — 장애 감지·진단·복구 자동화
---

> Analytics: `node scripts/log-event.mjs command_start name=incident` — 실행 시작 시 반드시 호출

프로덕션 장애 발생 시 체계적 대응. AWS DevOps Agent 패턴 참고.

## 사용법

```
/incident <url_or_description>
/incident "API 응답 시간 5초 초과"
/incident https://status.example.com/incident/123
```

## Step 1 — 상황 파악

장애 정보 수집:
- 에러 로그 (최근 50줄)
- 시스템 상태 (CPU, 메모리, 디스크)
- 최근 배포 이력 (`git log --oneline -5`)
- 의존 서비스 상태 (DB, Redis, 외부 API)

```bash
# 기본 시스템 상태
echo "=== System ===" && uptime && df -h / && free -m 2>/dev/null || vm_stat
echo "=== Recent Deploys ===" && git log --oneline -5
echo "=== Recent Errors ===" && tail -50 /var/log/app/error.log 2>/dev/null || echo "no log path configured"
```

## Step 2 — 영향 분류

| 레벨 | 기준 | 대응 |
|------|------|------|
| **SEV-1** | 전체 서비스 다운, 데이터 손실 | 즉시 복구, 모든 작업 중단 |
| **SEV-2** | 핵심 기능 장애, 50%+ 사용자 영향 | 1시간 내 대응 |
| **SEV-3** | 부분 기능 저하, 우회 가능 | 24시간 내 대응 |
| **SEV-4** | 사소한 이슈, UX 불편 | 다음 스프린트 |

## Step 3 — 근본 원인 분석

`/investigate` 에이전트 호출:
1. 타임라인 구성 (언제 시작? 언제 감지?)
2. 변경 사항 대조 (최근 배포/설정 변경)
3. 의존성 확인 (외부 서비스 장애?)
4. 5 Whys 분석

## Step 4 — 복구 실행

| 유형 | 조치 | 자동화 |
|------|------|--------|
| 배포 롤백 | `git revert` + 재배포 | 가능 (사용자 승인 후) |
| 스케일링 | 인스턴스 추가 / 리소스 확장 | 가능 (IaC) |
| 데이터 복구 | 백업 복원 | 반자동 (사용자 승인 필수) |
| 설정 수정 | env/config 변경 | 가능 |
| 외부 의존성 | fallback 활성화 / 대기 | 수동 모니터링 |

## Step 5 — 포스트모템

장애 해결 후 자동 생성:

```markdown
# Incident Postmortem — [날짜] [제목]

## 요약
- 시작: YYYY-MM-DD HH:MM
- 감지: YYYY-MM-DD HH:MM (감지 시간: Xm)
- 해결: YYYY-MM-DD HH:MM (총 소요: Xm)
- 영향: 사용자 N명, 기능 X

## 타임라인
...

## 근본 원인
...

## 재발 방지
- [ ] 조치 1
- [ ] 조치 2

## 교훈
...
```

저장: `.context/incidents/YYYY-MM-DD-<title>.md`
