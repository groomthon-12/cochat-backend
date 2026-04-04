# Slack API Integration Notes

이 문서는 `develop` 브랜치의 현재 Slack 연동 흐름을 기준으로, 실제 코드가 어떤 식으로 동작하는지와 로컬에서 어떤 검증을 했는지를 정리한 보강 문서다.

## 목적

- Slack 대화 내용을 우리 백엔드로 수집한다.
- 수집한 원본 이벤트를 `raw_events` 테이블에 저장한다.
- 이후 정규화와 AI 파이프라인은 저장된 원본 이벤트를 기준으로 후속 처리한다.

핵심 관점은 다음과 같다.

1. Slack은 원본 메시지 소스다.
2. 백엔드는 원본 이벤트를 먼저 저장한다.
3. 정규화는 `raw_event` 저장 이후에 수행된다.

## 현재 코드 기준 흐름

### 1. Slack OAuth 설치

Slack 연동 계정과 토큰 저장은 아래 엔드포인트에서 시작한다.

- `GET /api/v1/integrations/slack/oauth-url`
- `GET /api/v1/integrations/slack/callback`

관련 파일:

- [app/api/endpoints/integrations.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/api/endpoints/integrations.py)
- [app/integrations/slack/client.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/integrations/slack/client.py)
- [app/repositories/integration_repository.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/repositories/integration_repository.py)

처리 순서:

1. `/integrations/slack/oauth-url` 에서 Slack OAuth URL 생성
2. 사용자가 Slack 승인
3. `/integrations/slack/callback` 으로 code 전달
4. Slack access token 교환
5. `integration_accounts`, `integration_tokens` 저장

현재 구현은 Slack workspace를 `account_identifier=team_id` 기준으로 저장한다.

### 2. Slack webhook 수신

Slack 이벤트 수신은 아래 webhook 엔드포인트에서 처리한다.

- `POST /api/v1/webhooks/slack`

관련 파일:

- [app/ingress/slack_webhook.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/ingress/slack_webhook.py)

처리 순서:

1. `X-Slack-Request-Timestamp`, `X-Slack-Signature` 검증
2. `url_verification` 이면 challenge 응답
3. bot 메시지 무시
4. `message`, `app_mention` 이벤트만 계속 처리
5. `team_id` 로 `integration_accounts` 조회
6. `raw_events` 저장
7. 저장된 `raw_event.id` 를 들고 `normalize_message(...)` 호출

## raw_event 저장 구조

원본 이벤트 저장은 아래 repository 함수로 처리한다.

- [app/repositories/raw_event_repository.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/repositories/raw_event_repository.py)

현재 저장 필드:

- `provider`
- `integration_id`
- `provider_event_id`
- `event_type`
- `payload`
- `received_at`

즉 `raw_event` 는 “정규화 결과”가 아니라 “Slack이 보낸 원본 payload”를 저장하는 테이블이다.

## 로컬 검증 과정

로컬에서 실제로 확인한 내용은 다음과 같다.

### 확인 1. Postgres 준비

로컬 기본 포트 `5432` 는 다른 프로젝트가 사용 중이어서, `cochat-backend` 전용 Postgres를 `55432` 포트로 띄워 사용했다.

예시 `.env`:

```env
DATABASE_URL=postgresql://cochat:cochat_dev@localhost:55432/cochat
ASYNC_DATABASE_URL=postgresql+asyncpg://cochat:cochat_dev@localhost:55432/cochat
SLACK_SIGNING_SECRET=test-signing-secret
SLACK_CLIENT_ID=...
SLACK_CLIENT_SECRET=...
SLACK_REDIRECT_URI=http://localhost:8000/api/v1/integrations/slack/callback
SLACK_BOT_TOKEN=
```

### 확인 2. DB 테이블 생성

모델 기준으로 아래 테이블이 생성되는 것을 확인했다.

- `integration_accounts`
- `integration_tokens`
- `raw_events`
- 그 외 briefing / notification 관련 테이블

### 확인 3. integration_accounts seed

Slack workspace 식별용 row를 하나 넣고 webhook 수신을 테스트했다.

예시:

```sql
insert into integration_accounts (provider, account_identifier, account_name, status, created_at)
values ('slack', 'T0AQT172J6S', 'Jnu', 'active', now());
```

### 확인 4. 서명된 webhook 요청 직접 테스트

Slack 실제 호출 대신, 서명을 만들어 `POST /api/v1/webhooks/slack` 로 테스트 요청을 넣었다.

검증 payload 예시:

```json
{
  "team_id": "T0AQT172J6S",
  "event": {
    "type": "message",
    "user": "U0AQVC3QYD8",
    "channel": "C0ARPB3PARE",
    "ts": "1775301391.654399",
    "text": "raw event save test"
  }
}
```

### 확인 5. DB insert 결과

`raw_events` 테이블에 실제 row가 생성되는 것을 확인했다.

확인된 값:

- `provider = 'slack'`
- `integration_id = 1`
- `provider_event_id = '1775301391.654399'`
- `event_type = 'message'`

payload 확인 결과:

```json
{
  "ts": "1775301391.654399",
  "text": "raw event save test",
  "type": "message",
  "user": "U0AQVC3QYD8",
  "channel": "C0ARPB3PARE"
}
```

즉, **`raw_event` 저장 자체는 동작한다**고 확인했다.

## 현재 이슈

현재 webhook 전체 흐름은 `raw_event` 저장 이후 정규화 단계에서 깨진다.

원인:

- [app/ingress/slack_webhook.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/ingress/slack_webhook.py) 에서
  `normalize_message(..., event_type=event_type_raw)` 로 호출
- [app/integrations/slack/normalizer.py](/C:/Users/Admin/Desktop/GOORM/cochat-backend/app/integrations/slack/normalizer.py) 의
  `normalize_message` 시그니처는 `event_type` 인자를 받지 않음

실제 의미:

- `raw_event` 저장은 성공
- 그 이후 정규화 호출에서 `TypeError` 발생
- 따라서 “원본 저장은 됐지만 요청 전체는 실패” 상태

## 현재 구조 해석

현재 구현은 개념적으로 다음 순서를 따른다.

1. Slack에서 이벤트 수신
2. `raw_event` 저장
3. 저장된 `raw_event.id` 기준 정규화
4. 이후 AI 파이프라인으로 전달 예정

즉 `raw_event` 를 먼저 저장하고 그 뒤 정규화하는 구조 자체는 맞다.

다만 현재는 저장과 정규화가 **같은 webhook 핸들러 안에 붙어 있어서**, 역할 경계가 선명하게 분리되어 있지는 않다.

## 정리

- 현재 `develop` 기준 Slack은 **Slack API + webhook 기반**으로 연동되어 있다.
- OAuth를 통해 `integration_accounts`, `integration_tokens` 를 저장한다.
- 실제 이벤트는 `POST /webhooks/slack` 으로 들어온다.
- `raw_event` 저장은 실제로 검증됐다.
- 현재 실패 지점은 저장이 아니라 **정규화 함수 호출 규약 불일치**다.
- 따라서 원본 저장 기반으로 후속 정규화를 붙이는 방향 자체는 유지 가능하다.
